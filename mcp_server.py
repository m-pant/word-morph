#!/usr/bin/env python3
"""
MCP Server for Word Morph API

This MCP server provides access to the Word Morph API for finding semantically
similar Russian words with various transformations and filters.
"""
import asyncio
import json
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import httpx

# Create MCP server instance
app = Server("word-morph-api")

# API base URL (can be configured via environment variable)
import os
API_BASE_URL = os.getenv("WORD_MORPH_API_URL", "http://localhost:8081")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="search_similar_words",
            description="""Find semantically similar Russian words using Navec embeddings.

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
- Find words with transformations: word="гроза", shuffle_letters=true, preserve_first=true
- Return original words with transformations: word="гроза", shuffle_letters=true, return_source=true""",
            inputSchema={
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
                        "description": """Filter by part of speech. Options:
- noun: nouns
- verb, infn: verbs
- adjective, adjf, adjs: adjectives
- advb: adverbs
- verb_all: all verb forms
- participle: participles""",
                        "enum": [
                            "noun", "verb", "adjective", "adjf", "adjs", "infn",
                            "prtf", "prts", "grnd", "numr", "advb", "npro", "pred",
                            "prep", "conj", "prcl", "intj", "verb_all", "participle", "all"
                        ]
                    },
                    "normalize": {
                        "type": "boolean",
                        "description": "Convert words to base form (nominative singular for nouns, masculine nominative for adjectives, infinitive for verbs). Automatically removes duplicates.",
                        "default": False
                    },
                    "return_source": {
                        "type": "boolean",
                        "description": "Return original words along with transformed ones. Adds 'sources' field with {original, transformed} pairs.",
                        "default": False
                    },
                    "stride": {
                        "type": "integer",
                        "description": "Step for sampling words to get more diversity (0=sequential, 1=every other word, etc.)",
                        "minimum": 0,
                        "default": 0
                    },
                    "similarity_threshold": {
                        "type": "number",
                        "description": "Jaccard similarity threshold to filter out lexically similar words (0.0-1.0, recommended: 0.5-0.7)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.0
                    },
                    "random_mode": {
                        "type": "boolean",
                        "description": "Return random words from vocabulary instead of semantically similar ones",
                        "default": False
                    },
                    "shuffle_letters": {
                        "type": "boolean",
                        "description": "Randomly shuffle letters in words (respects letter_type and preserve filters)",
                        "default": False
                    },
                    "skip_letters": {
                        "type": "integer",
                        "description": "Number of random letters to skip/remove from each word",
                        "minimum": 0,
                        "default": 0
                    },
                    "show_skipped": {
                        "type": "boolean",
                        "description": "Show skipped letters as underscores (_) instead of removing them",
                        "default": False
                    },
                    "add_errors": {
                        "type": "boolean",
                        "description": "Replace random letters with similar ones to simulate typos",
                        "default": False
                    },
                    "letter_type": {
                        "type": "string",
                        "description": "Which letters to transform: all, only vowels (а,е,ё,и,о,у,ы,э,ю,я), or only consonants",
                        "enum": ["all", "vowels", "consonants"],
                        "default": "all"
                    },
                    "preserve_first": {
                        "type": "boolean",
                        "description": "Keep the first letter unchanged during transformations",
                        "default": False
                    },
                    "preserve_last": {
                        "type": "boolean",
                        "description": "Keep the last letter unchanged during transformations",
                        "default": False
                    }
                },
                "required": ["word"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    if name != "search_similar_words":
        raise ValueError(f"Unknown tool: {name}")

    # Build API URL
    api_url = f"{API_BASE_URL}/api/words"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Make request to Word Morph API
            response = await client.get(api_url, params=arguments)
            response.raise_for_status()
            data = response.json()

            # Format response
            query_info = data.get('query', {})
            results = data.get('results', [])
            sources = data.get('sources')

            # Build detailed response
            result_text = f"✓ Found {len(results)} words for '{query_info.get('word', arguments.get('word'))}':\n\n"
            result_text += ", ".join(results)

            # Add original words if return_source was used
            if sources:
                result_text += "\n\n📝 Original → Transformed:\n"
                for pair in sources:
                    result_text += f"  {pair['original']} → {pair['transformed']}\n"

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

            return [TextContent(
                type="text",
                text=result_text
            )]

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = error_data.get('message', str(e))
            except:
                error_detail = str(e)

            return [TextContent(
                type="text",
                text=f"❌ API Error ({e.response.status_code}): {error_detail}"
            )]

        except httpx.RequestError as e:
            return [TextContent(
                type="text",
                text=f"❌ Connection Error: {str(e)}\n\nMake sure Word Morph API is running at {API_BASE_URL}"
            )]

        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Unexpected Error: {str(e)}"
            )]


async def main():
    """Main entry point for MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
