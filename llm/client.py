from __future__ import annotations

import os
from openai import OpenAI

from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schemas import MeetingAnalysis


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured. Add it to .env.")
    return OpenAI(api_key=api_key)


def analyze_transcript(transcript: str, reference_date: str) -> MeetingAnalysis:
    if not transcript.strip():
        raise ValueError("Transcript is empty.")

    client = get_client()
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

    response = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(transcript, reference_date)},
        ],
        text_format=MeetingAnalysis,
    )

    if not response.output_parsed:
        raise RuntimeError("The LLM returned no structured result.")
    return response.output_parsed
