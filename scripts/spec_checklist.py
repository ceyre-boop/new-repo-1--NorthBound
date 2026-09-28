#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any, Iterable

import yaml
from yaml import YAMLError

VALID_IMAGE_STATUSES = {"have", "need", "replace", "rejected"}

REQUIRED_TOP_LEVEL = [
    "client",
    "package",
    "run_id",
    "brand",
    "pages",
    "images",
    "integrations",
    "seo",
    "constraints",
]


def walk_strings(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
        return
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_path = f"{path}.{key}" if path else str(key)
            yield from walk_strings(nested, nested_path)
        return
    if isinstance(value, list):
        for i, nested in enumerate(value):
            nested_path = f"{path}[{i}]"
            yield from walk_strings(nested, nested_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate intake completeness for client spec files")
    parser.add_argument("spec", type=pathlib.Path, help="Path to a spec YAML file")
    parser.add_argument(
        "--allow-empty-copy-slots",
        action="store_true",
        help="Allow empty copy slots without failing (does not bypass structural checks)",
    )
    parser.add_argument(
        "--allow-empty-slots",
        action="store_true",
        help="Deprecated alias for --allow-empty-copy-slots",
    )
    args = parser.parse_args()

    issues: list[str] = []
    try:
        with args.spec.open() as f:
            spec = yaml.safe_load(f)
    except (OSError, YAMLError) as exc:
        issues.append(f"could not parse YAML: {exc}")
        spec = {}

    if not isinstance(spec, dict):
        issues.append("spec root must be a mapping")
        spec = {}

    for key in REQUIRED_TOP_LEVEL:
        if key not in spec:
            issues.append(f"missing top-level key: {key}")

    pages = spec.get("pages")
    if pages is not None and not isinstance(pages, list):
        issues.append("pages must be a list")
        pages = []
    elif pages is None:
        pages = []

    images = spec.get("images") if isinstance(spec.get("images"), dict) else {}
    image_names = set(images.keys())

    seo = spec.get("seo")
    if seo is not None and not isinstance(seo, dict):
        issues.append("seo must be a mapping")
        seo = {}
    elif seo is None:
        seo = {}
    if "og_image" in seo and seo["og_image"] not in image_names:
        issues.append(f"seo.og_image references undeclared image: {seo['og_image']}")

    for page_i, page in enumerate(pages):
        if not isinstance(page, dict):
            issues.append(f"pages[{page_i}] must be a mapping")
            continue

        page_seo = page.get("seo")
        if page_seo is not None and not isinstance(page_seo, dict):
            issues.append(f"pages[{page_i}].seo must be a mapping")
            page_seo = {}
        elif page_seo is None:
            page_seo = {}
        if "og_image" in page_seo and page_seo["og_image"] not in image_names:
            issues.append(
                f"pages[{page_i}].seo.og_image references undeclared image: {page_seo['og_image']}"
            )

        sections = page.get("sections")
        if sections is not None and not isinstance(sections, list):
            issues.append(f"pages[{page_i}].sections must be a list")
            sections = []
        elif sections is None:
            sections = []

        for section_i, section in enumerate(sections):
            if not isinstance(section, dict):
                issues.append(f"pages[{page_i}].sections[{section_i}] must be a mapping")
                continue

            section_images = section.get("images", [])
            if not isinstance(section_images, list):
                issues.append(f"pages[{page_i}].sections[{section_i}].images must be a list")
                section_images = []

            for image in section_images or []:
                if not isinstance(image, str):
                    issues.append(
                        f"pages[{page_i}].sections[{section_i}].images contains non-string reference"
                    )
                    continue
                if image not in image_names:
                    issues.append(
                        f"pages[{page_i}].sections[{section_i}].images references undeclared image: {image}"
                    )

            copy = section.get("copy", {})
            if not isinstance(copy, dict):
                issues.append(f"pages[{page_i}].sections[{section_i}].copy must be a mapping")
                continue
            for slot_path, slot_value in walk_strings(copy, f"pages[{page_i}].sections[{section_i}].copy"):
                if isinstance(slot_value, str) and slot_value.strip() == "":
                    issues.append(f"empty copy slot: {slot_path}")

    for image_name, image_meta in images.items():
        if not isinstance(image_meta, dict):
            issues.append(f"images.{image_name} must be a mapping")
            continue

        status = image_meta.get("status")
        if "alt" not in image_meta:
            issues.append(f"images.{image_name}.alt is required")
            alt = None
        else:
            alt = image_meta.get("alt")
        if status not in VALID_IMAGE_STATUSES:
            issues.append(
                f"images.{image_name}.status must be one of {sorted(VALID_IMAGE_STATUSES)}"
            )
        if not isinstance(alt, str):
            issues.append(f"images.{image_name}.alt must be a string")
        elif status != "rejected" and alt.strip() == "":
            issues.append(f"empty alt slot: images.{image_name}.alt")

    if args.allow_empty_slots or args.allow_empty_copy_slots:
        issues = [
            issue
            for issue in issues
            if not issue.startswith("empty copy slot:")
        ]

    if issues:
        print("SPEC CHECKLIST FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("SPEC CHECKLIST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
