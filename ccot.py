"""
Compositional Chain-of-Thought video captioning.

This mode first asks the vision-language model for a compact scene graph, then
generates styled captions from that graph plus the original ordered frames.
"""

import json
import random
import sys
import time

from zero_shot import DEFAULT_MODEL, STYLES

CAPTION_MODES = ("zero_shot", "ccot")


def normalize_caption_mode(mode):
    """Return a canonical caption mode name."""
    normalized = (mode or "zero_shot").strip().lower().replace("-", "_")
    aliases = {
        "zero": "zero_shot",
        "zeroshot": "zero_shot",
        "zero_shot": "zero_shot",
        "direct": "zero_shot",
        "ccot": "ccot",
        "compositional_cot": "ccot",
        "compositional_chain_of_thought": "ccot",
        "scene_graph": "ccot",
    }
    if normalized not in aliases:
        raise ValueError(f"Unknown CAPTION_MODE '{mode}'. Expected one of: {', '.join(CAPTION_MODES)}")
    return aliases[normalized]


def _content_with_frames(prompt, frames_b64):
    content = [{"type": "text", "text": prompt}]
    for f in frames_b64:
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{f}"}}
        )
    return content


def _chat_json(client, model, content, temperature, max_tokens, max_retries=3, timeout=25):
    """Call the model and return raw content, retrying transient failures."""
    raw = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                response_format={"type": "json_object"},
                extra_body={"thinking": {"type": "disabled"}},
            )
            raw = resp.choices[0].message.content.strip()
            break
        except Exception as e:
            is_retryable = (
                "timeout" in str(e).lower() or
                "429" in str(e) or
                "500" in str(e) or
                "503" in str(e)
            )
            if attempt < max_retries and is_retryable:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"API call failed (attempt {attempt + 1}/{max_retries + 1}): {e}", file=sys.stderr)
                print(f"Retrying in {wait_time:.1f}s...", file=sys.stderr)
                time.sleep(wait_time)
            else:
                raise

    if raw is None:
        raise ValueError(f"No response from model after {max_retries + 1} attempts")
    return raw


def _parse_json_object(raw):
    """Extract and parse a JSON object from model output."""
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model did not return valid JSON: {raw}") from exc


def _validate_styles(styles):
    invalid = [s for s in styles if s not in STYLES]
    if invalid:
        raise ValueError(f"Unknown styles: {', '.join(invalid)}")


def _style_lines(styles):
    return "\n".join(
        f"{i+1}. {style}: {STYLES[style]['prompt']}"
        for i, style in enumerate(styles)
    )


def _captions_from_json(parsed, styles, raw):
    for style in styles:
        if style not in parsed:
            raise ValueError(f"Missing caption for style '{style}' in model output: {raw}")

    return {style: str(parsed[style]).strip() for style in styles}


def generate_scene_graph(frames_b64, styles, client, model=DEFAULT_MODEL, max_retries=3):
    """Generate a compact scene graph for the ordered video frames."""
    _validate_styles(styles)
    prompt = (
        "You are a video scene graph extractor. Watch the ordered frames and create a compact "
        "scene graph that captures only visible evidence needed to caption the video.\n\n"
        "Track objects, people, attributes, actions, spatial relationships, and temporal changes "
        "across frames. Avoid guesses. Mark uncertainty explicitly when evidence is unclear. "
        "Use short phrases, not prose.\n\n"
        "Return ONLY a valid JSON object with this format:\n"
        "{\n"
        '  "scene_graph": {\n'
        '    "entities": [{"id": "e1", "name": "...", "attributes": ["..."]}],\n'
        '    "relations": [{"subject": "e1", "predicate": "...", "object": "e2"}],\n'
        '    "actions": [{"actor": "e1", "verb": "...", "target": "e2", "frames": "early|middle|late|all"}],\n'
        '    "setting": ["..."],\n'
        '    "temporal_events": ["..."],\n'
        '    "uncertainty": ["..."]\n'
        "  }\n"
        "}"
    )
    raw = _chat_json(
        client=client,
        model=model,
        content=_content_with_frames(prompt, frames_b64),
        temperature=0.2,
        max_tokens=900,
        max_retries=max_retries,
        timeout=30,
    )
    parsed = _parse_json_object(raw)
    scene_graph = parsed.get("scene_graph")
    if not isinstance(scene_graph, dict):
        raise ValueError(f"Missing scene_graph in model output: {raw}")
    return scene_graph


def caption_all_styles(frames_b64, styles, client, model=DEFAULT_MODEL, max_retries=3):
    """Generate a scene graph first, then caption from graph plus frames."""
    _validate_styles(styles)
    scene_graph = generate_scene_graph(frames_b64, styles, client, model=model, max_retries=max_retries)
    scene_graph_json = json.dumps(scene_graph, ensure_ascii=True, separators=(",", ":"))
    prompt = (
        "You are a video captioning assistant using Compositional Chain-of-Thought. "
        "Use the scene graph as your factual anchor, and verify it against the ordered frames. "
        "Do not invent objects, actions, relationships, or jokes that conflict with the scene graph.\n\n"
        f"Scene graph JSON:\n{scene_graph_json}\n\n"
        f"Produce exactly {len(styles)} captions, one for each style listed below.\n\n"
        f"{_style_lines(styles)}\n\n"
        "Return ONLY a valid JSON object. Do not explain, do not think out loud, "
        "do not use markdown code blocks, do not include any text before or after the JSON. "
        "Each key must be exactly the style name, and each value must be the caption string.\n\n"
        "Required JSON format:\n"
        "{" + ", ".join(f'"{style}": "..."' for style in styles) + "}"
    )
    temperature = max(STYLES[s]["temperature"] for s in styles)
    raw = _chat_json(
        client=client,
        model=model,
        content=_content_with_frames(prompt, frames_b64),
        temperature=temperature,
        max_tokens=512,
        max_retries=max_retries,
    )
    parsed = _parse_json_object(raw)
    return _captions_from_json(parsed, styles, raw)


def caption(frames_b64, style, client, model=DEFAULT_MODEL):
    """CCoT caption the frames in the given style."""
    return caption_all_styles(frames_b64, [style], client, model=model)[style]
