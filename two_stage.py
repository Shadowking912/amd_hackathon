"""
Two-stage stylistic video captioning.

Stage 1 asks the VLM for a factual description from frames.
Stage 2 rewrites that description into requested styles.
"""

import argparse
import json
import os
import random
import sys
import time

from openai import OpenAI

from zero_shot import STYLES, caption_all_styles, extract_frames

DEFAULT_MODEL = os.environ.get("ALLOWED_MODELS", "accounts/fireworks/models/qwen3p7-plus").split(",")[0].strip()
DEFAULT_MODEL_VISION = os.environ.get("MODEL_VISION", DEFAULT_MODEL).strip()
DEFAULT_MODEL_STYLE = os.environ.get("MODEL_STYLE", DEFAULT_MODEL).strip()
DEFAULT_CAPTION_MODE = os.environ.get("CAPTION_MODE", "two_stage").strip()

FACTUAL_DESCRIPTION_PROMPT = (
    "You are a factual video analyst. Watch the ordered frames and write a concise "
    "objective description of what is visibly happening across the clip. Include the "
    "main subjects, setting, actions, notable objects, and clear sequence changes. "
    "Do not add jokes, opinions, intent, emotion, identity guesses, or facts not "
    "visible in the frames. Return only the description text."
)

VERIFY_DESCRIPTION_PROMPT = (
    "You are a fact-checker. Review this video description against the actual frames. "
    "For each claim in the description:\n"
    "1. Check if it matches what you see in the frames\n"
    "2. If wrong or too generic, correct or expand it\n"
    "3. If missing important details visible in frames, add them\n"
    "4. Remove any statements not visible in frames\n\n"
    "Return ONLY the corrected, verified description. Do not explain your changes."
)

STYLE_REWRITE_PROMPTS = {
    "formal": (
        "Write one concise formal caption in complete sentences. State the main "
        "subject, setting, and visible action or change in a professional, neutral "
        "tone. No humor, opinions, or emojis."
    ),
    "sarcastic": (
        "Write one concise sarcastic caption with dry, understated irony. Base the "
        "joke on the specific action, subject, or setting rather than a generic "
        "observation. Keep it playful and PG; do not target protected traits, use "
        "slurs, or emojis."
    ),
    "humorous_tech": (
        "Write one concise funny caption using a fresh programming, software, or "
        "DevOps metaphor that fits the specific action. Technical references and "
        "figurative comparisons are encouraged. Keep it understandable, original, "
        "and PG; do not use emojis."
    ),
    "humorous_non_tech": (
        "Write one concise, light-hearted everyday-humor caption based on the specific "
        "action in the verified description. Make it relatable and playful without "
        "technical jargon, cruelty, stereotypes, or emojis. Do not invent people, "
        "objects, locations, or outcomes."
    ),
}

STYLE_GROUNDING_RULE = (
    "Grounding rule: preserve the factual subject, setting, and visible action from "
    "the verified description. The formal caption must remain strictly factual. "
    "Sarcastic and humorous captions may add clearly figurative jokes, cultural "
    "references, or metaphors, but must not introduce invented people, objects, "
    "actions, causes, or outcomes as if they were visible in the video."
)


def _create_completion_with_retries(
    client,
    *,
    model,
    messages,
    temperature,
    max_tokens,
    max_retries,
    response_format=None,
):
    """Call chat completions with exponential backoff for transient failures."""
    for attempt in range(max_retries + 1):
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout": 25,
                "extra_body": {"thinking": {"type": "disabled"}},
            }
            if response_format is not None:
                kwargs["response_format"] = response_format
            resp = client.chat.completions.create(**kwargs)
            choice = resp.choices[0]
            message = choice.message
            content = (message.content or "").strip()
            if not content or content in ("{}", "{\n}"):
                print(
                    "[Empty model content] "
                    f"finish_reason={getattr(choice, 'finish_reason', None)!r} "
                    f"refusal={getattr(message, 'refusal', None)!r} "
                    f"message={message!r}",
                    file=sys.stderr,
                )
            return content
        except Exception as e:
            is_retryable = (
                "timeout" in str(e).lower()
                or "429" in str(e)
                or "500" in str(e)
                or "503" in str(e)
            )
            if attempt < max_retries and is_retryable:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"API call failed (attempt {attempt + 1}/{max_retries + 1}): {e}", file=sys.stderr)
                print(f"Retrying in {wait_time:.1f}s...", file=sys.stderr)
                time.sleep(wait_time)
            else:
                raise

    raise ValueError(f"No response from model after {max_retries + 1} attempts")


def _parse_style_json(raw, styles):
    """Parse and validate model JSON for style captions."""
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model did not return valid JSON: {raw}") from exc

    for style in styles:
        if style not in parsed:
            raise ValueError(f"Missing caption for style '{style}' in model output: {raw}")

    return {style: str(parsed[style]).strip() for style in styles}


def _validate_styles(styles):
    invalid = [s for s in styles if s not in STYLES]
    if invalid:
        raise ValueError(f"Unknown styles: {', '.join(invalid)}")


def describe_video_facts(frames_b64, client, model=DEFAULT_MODEL_VISION, max_retries=3):
    """Stage 1: ask the VLM for a factual description of the visible video content."""
    content = [{"type": "text", "text": FACTUAL_DESCRIPTION_PROMPT}]
    for frame in frames_b64:
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame}"}}
        )

    return _create_completion_with_retries(
        client,
        model=model,
        messages=[{"role": "user", "content": content}],
        temperature=0.3,
        max_tokens=1024,
        max_retries=max_retries,
    )


def verify_description(frames_b64, description, client, model=DEFAULT_MODEL_VISION, max_retries=3):
    """Stage 1b: verify and correct the description against the actual frames."""
    content = [
        {
            "type": "text",
            "text": f"{VERIFY_DESCRIPTION_PROMPT}\n\nCurrent description:\n{description}"
        }
    ]
    for frame in frames_b64:
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame}"}}
        )

    verified = _create_completion_with_retries(
        client,
        model=model,
        messages=[{"role": "user", "content": content}],
        temperature=0.1,  # Very strict - just fact-checking, not creative
        max_tokens=1024,
        max_retries=max_retries,
    )
    return verified


def rewrite_description_all_styles(description, styles, client, model=DEFAULT_MODEL_STYLE, max_retries=3):
    """Stage 2: rewrite a factual description into each requested style."""
    _validate_styles(styles)

    style_lines = "\n".join(
        f"{i+1}. {style}: {STYLE_REWRITE_PROMPTS[style]}"
        for i, style in enumerate(styles)
    )
    prompt = (
        "You are a caption rewriting assistant. Rewrite the factual video description "
        f"into exactly {len(styles)} captions, one for each style listed below.\n\n"
        f"{STYLE_GROUNDING_RULE}\n\n"
        "Factual description:\n"
        f"{description}\n\n"
        f"{style_lines}\n\n"
        "Grounding rule: preserve the factual subject, setting, and visible action from "
        "the description. The formal caption must remain strictly factual. Sarcastic "
        "and humorous captions may add clearly figurative jokes, cultural references, "
        "or metaphors, but must not introduce invented people, objects, actions, causes, "
        "or outcomes as if they were visible in the video.\n\n"
        "Return ONLY a valid JSON object. Do not explain, do not think out loud, "
        "do not use markdown code blocks, do not include any text before or after the JSON. "
        "Each key must be exactly the style name, and each value must be the caption string.\n\n"
        "Required JSON format:\n"
        "{" + ", ".join(f'"{style}": "..."' for style in styles) + "}"
    )

    temperature = max(STYLES[s]["temperature"] for s in styles)
    messages = [{"role": "user", "content": prompt}]
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            raw = _create_completion_with_retries(
                client,
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=1024,
                max_retries=max_retries,
                response_format={"type": "json_object"},
            )
            print(f"[Stage 2 raw response attempt {attempt + 1}] {raw!r}", file=sys.stderr)
            return _parse_style_json(raw, styles)
        except ValueError as exc:
            last_error = exc
            if attempt < max_retries:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(
                    f"Stage 2 returned incomplete JSON (attempt {attempt + 1}/{max_retries + 1}): {exc}",
                    file=sys.stderr,
                )
                print(f"Retrying Stage 2 in {wait_time:.1f}s...", file=sys.stderr)
                time.sleep(wait_time)
            else:
                raise

    raise last_error or ValueError("Stage 2 produced no valid JSON response")


def caption_all_styles_two_stage(frames_b64, styles, client, model_vision=DEFAULT_MODEL_VISION, model_style=DEFAULT_MODEL_STYLE, max_retries=3):
    """Caption frames via 3-stage pipeline: describe → verify → rewrite styles."""
    _validate_styles(styles)
    
    # Stage 1: Generate factual description
    description = describe_video_facts(frames_b64, client, model=model_vision, max_retries=max_retries)
    print(f"[Stage 1 description] {len(description)} chars", file=sys.stderr)
    
    # Stage 1b: Verify and correct description against frames
    verified_description = verify_description(
        frames_b64,
        description,
        client,
        model=model_vision,
        max_retries=max_retries,
    )
    print(f"[Stage 1b verified] {len(verified_description)} chars", file=sys.stderr)
    
    # Stage 2: Rewrite verified description into requested styles
    return rewrite_description_all_styles(
        verified_description,
        styles,
        client,
        model=model_style,
        max_retries=max_retries,
    )


CAPTION_MODES = {
    "zero_shot": caption_all_styles,
    "two_stage": caption_all_styles_two_stage,
}


def caption_all_styles_with_mode(
    frames_b64,
    styles,
    client,
    mode=DEFAULT_CAPTION_MODE,
    model=DEFAULT_MODEL,
    model_vision=DEFAULT_MODEL_VISION,
    model_style=DEFAULT_MODEL_STYLE,
    max_retries=3,
):
    """Caption frames using a named mode."""
    mode = str(mode).strip()
    if mode not in CAPTION_MODES:
        raise ValueError(f"Unknown caption mode '{mode}'. Expected one of: {', '.join(CAPTION_MODES)}")
    
    if mode == "two_stage":
        return CAPTION_MODES[mode](
            frames_b64,
            styles,
            client,
            model_vision=model_vision,
            model_style=model_style,
            max_retries=max_retries,
        )
    else:
        return CAPTION_MODES[mode](
            frames_b64,
            styles,
            client,
            model=model,
            max_retries=max_retries,
        )


def caption(frames_b64, style, client, model=DEFAULT_MODEL, mode=DEFAULT_CAPTION_MODE):
    """Caption the frames in the given style using a named mode."""
    return caption_all_styles_with_mode(frames_b64, [style], client, mode=mode, model=model)[style]


def main():
    parser = argparse.ArgumentParser(description="Two-stage stylistic video captioning.")
    parser.add_argument("video", help="Path to the input video file.")
    parser.add_argument("style", nargs="?", choices=list(STYLES), help="Single style (default: all).")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Fireworks model id.")
    parser.add_argument("--model-vision", default=DEFAULT_MODEL_VISION, help="Vision model for stages 1 & 1b.")
    parser.add_argument("--model-style", default=DEFAULT_MODEL_STYLE, help="Style model for stage 2.")
    parser.add_argument("--num-frames", type=int, default=16,
                        help="Frames sampled evenly across the whole clip.")
    parser.add_argument("--fps", type=float, default=None,
                        help="Alternative to --num-frames: sample at a constant rate.")
    args = parser.parse_args()

    frames = extract_frames(args.video, num_frames=args.num_frames, fps=args.fps)
    print(f"[{len(frames)} frames sampled from {args.video}]", file=sys.stderr)
    client = OpenAI(
        api_key=os.environ["FIREWORKS_API_KEY"],
        base_url=os.environ["FIREWORKS_BASE_URL"],
    )

    styles = [args.style] if args.style else list(STYLES)
    captions = caption_all_styles_two_stage(
        frames,
        styles,
        client,
        model_vision=args.model_vision,
        model_style=args.model_style,
    )
    for style, text in captions.items():
        print(f"{style:18s} -> {text}")


if __name__ == "__main__":
    main()
