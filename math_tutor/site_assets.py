"""Site asset path and href helpers for generated site output."""

from __future__ import annotations

import html
import os
import shutil
from pathlib import Path


def link_tag(
    path: Path,
    output_dir: Path,
    site_dir: Path,
    label: str,
    base_path: str,
    css_class: str = "",
) -> str:
    href = build_site_href(path=path, output_dir=output_dir, site_dir=site_dir, base_path=base_path)
    class_attr = f' class="{html.escape(css_class)}"' if css_class else ""
    return f'<a href="{html.escape(href)}"{class_attr}>{html.escape(label)}</a>'


def resolve_site_asset_path(*, path: Path, output_dir: Path, site_dir: Path, deploy_assets: bool) -> Path:
    try:
        relative_to_output = path.relative_to(output_dir)
    except ValueError:
        return path

    deployed_copy = site_dir / relative_to_output
    if not deploy_assets:
        if deployed_copy.exists():
            return deployed_copy
        return path

    deployed_copy.parent.mkdir(parents=True, exist_ok=True)
    if not deployed_copy.exists() or path.stat().st_mtime_ns != deployed_copy.stat().st_mtime_ns:
        shutil.copy2(path, deployed_copy)
    return deployed_copy


def build_site_href(*, path: Path, output_dir: Path, site_dir: Path, base_path: str) -> str:
    deploy_assets = should_copy_site_assets(output_dir=output_dir, site_dir=site_dir, base_path=base_path)
    resolved_path = resolve_site_asset_path(
        path=path,
        output_dir=output_dir,
        site_dir=site_dir,
        deploy_assets=deploy_assets,
    )

    if base_path:
        try:
            relative_to_site = resolved_path.relative_to(site_dir).as_posix()
            return f"{base_path}{relative_to_site}"
        except ValueError:
            pass

    rel = Path(os.path.relpath(resolved_path, start=site_dir)).as_posix()
    return rel


def determine_base_path(*, raw_base_path: str, output_dir: Path, site_dir: Path) -> str:
    del output_dir, site_dir
    normalized = normalize_base_path(raw_base_path)
    if normalized:
        return normalized
    return ""


def normalize_base_path(value: str) -> str:
    if not value:
        return ""
    stripped = value.strip().strip("/")
    if not stripped:
        return ""
    return f"/{stripped}/"


def is_deploy_site_dir(*, output_dir: Path, site_dir: Path) -> bool:
    if not site_dir.is_relative_to(output_dir):
        return True
    try:
        relative_parts = site_dir.relative_to(output_dir).parts
    except ValueError:
        return False
    return "deploy" in relative_parts


def should_copy_site_assets(*, output_dir: Path, site_dir: Path, base_path: str) -> bool:
    return bool(base_path) or is_deploy_site_dir(output_dir=output_dir, site_dir=site_dir)
