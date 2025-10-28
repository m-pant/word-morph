#!/usr/bin/env python3
"""
MCP Server HTTP Wrapper for Word Morph API

This version exposes the MCP server over HTTP for use with tools like n8n.
It provides a REST API that wraps MCP protocol calls.
"""
import asyncio
import json
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field
import httpx
import uvicorn
import os

# API base URL (can be configured via environment variable)
API_BASE_URL = os.getenv("WORD_MORPH_API_URL", "http://localhost:8081")

app = FastAPI(
    title="Word Morph MCP HTTP Server",
    description="HTTP wrapper for Word Morph MCP server, compatible with n8n MCP Client",
    version="1.0.0"
)


class SearchRequest(BaseModel):
    """Request model for word search"""
    word: str = Field(..., description="The Russian word to search for (required, in Cyrillic)")
    count: Optional[int] = Field(10, ge=1, le=100, description="Number of words to return")
    pos_filter: Optional[str] = Field(None, description="Filter by part of speech (noun, verb, adjective, etc.)")
    normalize: Optional[bool] = Field(False, description="Convert words to base form")
    stride: Optional[int] = Field(0, ge=0, description="Step for sampling words")
    similarity_threshold: Optional[float] = Field(0.0, ge=0.0, le=1.0, description="Jaccard similarity threshold")
    random_mode: Optional[bool] = Field(False, description="Return random words")
    shuffle_letters: Optional[bool] = Field(False, description="Randomly shuffle letters")
    skip_letters: Optional[int] = Field(0, ge=0, description="Number of letters to skip")
    show_skipped: Optional[bool] = Field(False, description="Show skipped letters as underscores")
    add_errors: Optional[bool] = Field(False, description="Add typos")
    letter_type: Optional[str] = Field("all", description="Which letters to transform")
    preserve_first: Optional[bool] = Field(False, description="Keep first letter unchanged")
    preserve_last: Optional[bool] = Field(False, description="Keep last letter unchanged")


class MCPToolCall(BaseModel):
    """MCP tool call format"""
    name: str
    arguments: Dict[str, Any]


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request format"""
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    method: str
    params: Optional[Dict[str, Any]] = None


@app.post("/")
async def jsonrpc_handler(request: JSONRPCRequest):
    """JSON-RPC 2.0 endpoint for n8n MCP Client compatibility"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Received JSON-RPC request: method={request.method}, id={request.id}, params={request.params}")

    try:
        # Handle initialize method for MCP handshake
        if request.method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "word-morph-mcp",
                        "version": "1.0.0"
                    }
                }
            }

        elif request.method == "tools/list":
            # Return tools list
            tools_data = await list_tools()
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": tools_data
            }

        elif request.method == "tools/call":
            # Call tool
            if not request.params:
                return {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params"
                    }
                }

            tool_name = request.params.get("name")
            tool_arguments = request.params.get("arguments", {})

            if not tool_name:
                return {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "error": {
                        "code": -32602,
                        "message": "Missing 'name' parameter"
                    }
                }

            # Call the tool
            tool_call = MCPToolCall(name=tool_name, arguments=tool_arguments)
            result = await call_tool(tool_call)

            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": result
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                }
            }

    except HTTPException as e:
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {
                "code": e.status_code,
                "message": e.detail
            }
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }


@app.get("/sse")
async def sse_get_handler(request: Request):
    """SSE endpoint for GET requests (n8n HTTP Streamable handshake)"""
    async def event_generator():
        # Keep connection open for streaming
        # n8n might use this to establish the connection
        yield {
            "event": "connected",
            "data": json.dumps({"status": "connected", "service": "word-morph-mcp"})
        }
        # Keep alive
        while True:
            await asyncio.sleep(30)
            yield {
                "event": "ping",
                "data": json.dumps({"type": "keepalive"})
            }

    return EventSourceResponse(event_generator())


@app.post("/sse")
async def sse_handler(request: Request):
    """SSE endpoint for HTTP Streamable transport (n8n compatibility)"""
    import logging
    logger = logging.getLogger(__name__)

    async def event_generator():
        try:
            # Read the request body
            body = await request.json()
            logger.info(f"SSE received: {body}")

            # Process as JSON-RPC request
            jsonrpc_request = JSONRPCRequest(**body)

            # Handle initialize method
            if jsonrpc_request.method == "initialize":
                result = {
                    "jsonrpc": "2.0",
                    "id": jsonrpc_request.id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "word-morph-mcp",
                            "version": "1.0.0"
                        }
                    }
                }
                yield {
                    "event": "message",
                    "data": json.dumps(result)
                }

            elif jsonrpc_request.method == "tools/list":
                # Return tools list
                tools_data = await list_tools()
                result = {
                    "jsonrpc": "2.0",
                    "id": jsonrpc_request.id,
                    "result": tools_data
                }
                yield {
                    "event": "message",
                    "data": json.dumps(result)
                }

            elif jsonrpc_request.method == "tools/call":
                # Call tool
                if not jsonrpc_request.params:
                    error_result = {
                        "jsonrpc": "2.0",
                        "id": jsonrpc_request.id,
                        "error": {
                            "code": -32602,
                            "message": "Invalid params"
                        }
                    }
                    yield {
                        "event": "message",
                        "data": json.dumps(error_result)
                    }
                    return

                tool_name = jsonrpc_request.params.get("name")
                tool_arguments = jsonrpc_request.params.get("arguments", {})

                if not tool_name:
                    error_result = {
                        "jsonrpc": "2.0",
                        "id": jsonrpc_request.id,
                        "error": {
                            "code": -32602,
                            "message": "Missing 'name' parameter"
                        }
                    }
                    yield {
                        "event": "message",
                        "data": json.dumps(error_result)
                    }
                    return

                # Call the tool
                tool_call = MCPToolCall(name=tool_name, arguments=tool_arguments)
                result_data = await call_tool(tool_call)

                result = {
                    "jsonrpc": "2.0",
                    "id": jsonrpc_request.id,
                    "result": result_data
                }
                yield {
                    "event": "message",
                    "data": json.dumps(result)
                }

            else:
                error_result = {
                    "jsonrpc": "2.0",
                    "id": jsonrpc_request.id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {jsonrpc_request.method}"
                    }
                }
                yield {
                    "event": "message",
                    "data": json.dumps(error_result)
                }

        except Exception as e:
            error_result = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            yield {
                "event": "message",
                "data": json.dumps(error_result)
            }

    return EventSourceResponse(event_generator())


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "word-morph-mcp-http"}


@app.get("/tools")
async def list_tools():
    """List available MCP tools (MCP protocol compatible)"""
    return {
        "tools": [
            {
                "name": "search_similar_words",
                "description": """Find semantically similar Russian words using Navec embeddings.

Features:
- Semantic similarity search based on word embeddings
- Part-of-speech filtering (nouns, verbs, adjectives, etc.)
- Word normalization to base form (nominative singular)
- Text transformations (shuffle, skip letters, add errors)
- Stride sampling for diverse results
- Similarity threshold filtering

Examples:
- Find 5 similar nouns: word="дом", count=5, pos_filter="noun"
- Find normalized adjectives: word="красный", pos_filter="adjective", normalize=true
- Find words with transformations: word="гроза", shuffle_letters=true, preserve_first=true""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "word": {
                            "type": "string",
                            "description": "The Russian word to search for (required, in Cyrillic)"
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of words to return (1-100)",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10
                        },
                        "pos_filter": {
                            "type": "string",
                            "description": "Filter by part of speech",
                            "enum": [
                                "noun", "verb", "adjective", "adjf", "adjs", "infn",
                                "prtf", "prts", "grnd", "numr", "advb", "npro", "pred",
                                "prep", "conj", "prcl", "intj", "verb_all", "participle", "all"
                            ]
                        },
                        "normalize": {
                            "type": "boolean",
                            "description": "Convert words to base form",
                            "default": False
                        },
                        "stride": {
                            "type": "integer",
                            "description": "Step for sampling words",
                            "minimum": 0,
                            "default": 0
                        },
                        "similarity_threshold": {
                            "type": "number",
                            "description": "Jaccard similarity threshold (0.0-1.0)",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "default": 0.0
                        },
                        "random_mode": {
                            "type": "boolean",
                            "description": "Return random words",
                            "default": False
                        },
                        "shuffle_letters": {
                            "type": "boolean",
                            "description": "Randomly shuffle letters",
                            "default": False
                        },
                        "skip_letters": {
                            "type": "integer",
                            "description": "Number of random letters to skip",
                            "minimum": 0,
                            "default": 0
                        },
                        "show_skipped": {
                            "type": "boolean",
                            "description": "Show skipped letters as underscores",
                            "default": False
                        },
                        "add_errors": {
                            "type": "boolean",
                            "description": "Add typos",
                            "default": False
                        },
                        "letter_type": {
                            "type": "string",
                            "description": "Which letters to transform",
                            "enum": ["all", "vowels", "consonants"],
                            "default": "all"
                        },
                        "preserve_first": {
                            "type": "boolean",
                            "description": "Keep first letter unchanged",
                            "default": False
                        },
                        "preserve_last": {
                            "type": "boolean",
                            "description": "Keep last letter unchanged",
                            "default": False
                        }
                    },
                    "required": ["word"]
                }
            }
        ]
    }


@app.post("/tools/call")
async def call_tool(tool_call: MCPToolCall):
    """Execute MCP tool call (MCP protocol compatible)"""
    if tool_call.name != "search_similar_words":
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_call.name}")

    # Build API URL
    api_url = f"{API_BASE_URL}/api/words"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Make request to Word Morph API
            response = await client.get(api_url, params=tool_call.arguments)
            response.raise_for_status()
            data = response.json()

            # Format response
            query_info = data.get('query', {})
            results = data.get('results', [])

            # Build detailed response
            result_text = f"✓ Found {len(results)} words for '{query_info.get('word', tool_call.arguments.get('word'))}':\n\n"
            result_text += ", ".join(results)

            # Add query details if filters/transformations were applied
            details = []
            if query_info.get('pos_filter'):
                details.append(f"POS filter: {query_info['pos_filter']}")
            if query_info.get('normalize'):
                details.append("Normalized to base form")
            if query_info.get('stride', 0) > 0:
                details.append(f"Stride: {query_info['stride']}")
            if query_info.get('similarity_threshold', 0) > 0:
                details.append(f"Similarity threshold: {query_info['similarity_threshold']}")
            if query_info.get('random_mode'):
                details.append("Random mode")

            transformations = query_info.get('transformations', {})
            if transformations.get('shuffle_letters'):
                details.append("Letters shuffled")
            if transformations.get('skip_letters', 0) > 0:
                details.append(f"Skip {transformations['skip_letters']} letters")
            if transformations.get('add_errors'):
                details.append("Errors added")

            if details:
                result_text += f"\n\nApplied: {', '.join(details)}"

            return {
                "content": [
                    {
                        "type": "text",
                        "text": result_text
                    }
                ],
                "results": results,
                "query": query_info
            }

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = error_data.get('message', str(e))
            except:
                error_detail = str(e)

            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"API Error: {error_detail}"
            )

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Connection Error: {str(e)}. Make sure Word Morph API is running at {API_BASE_URL}"
            )


@app.post("/search")
async def search_words(request: SearchRequest):
    """Simplified search endpoint (direct API wrapper for easier use)"""
    # Convert request to dict and remove None values
    params = request.dict(exclude_none=True)

    api_url = f"{API_BASE_URL}/api/words"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()

            return data

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = error_data.get('message', str(e))
            except:
                error_detail = str(e)

            raise HTTPException(
                status_code=e.response.status_code,
                detail=error_detail
            )

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Connection Error: {str(e)}"
            )


if __name__ == "__main__":
    port = int(os.getenv("MCP_HTTP_PORT", "8082"))
    uvicorn.run(app, host="0.0.0.0", port=port)
