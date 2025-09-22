import json
import logging
import re
from dataclasses import dataclass

from backoffice.domain.entities.ebook_structure import EbookStructure

logger = logging.getLogger(__name__)


@dataclass
class ChapterInfo:
    title: str
    level: int
    anchor: str
    content: str


@dataclass
class TOCEntry:
    title: str
    anchor: str
    level: int


class ContentParser:
    def __init__(self):
        self.chapter_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def parse_markdown_content(self, content: str) -> list[ChapterInfo]:
        chapters = []
        lines = content.split("\n")
        current_chapter = None
        current_content_lines = []

        for line in lines:
            header_match = self.chapter_pattern.match(line)

            if header_match:
                level = len(header_match.group(1))

                # Si c'est un H1, finir le chapitre précédent et commencer un nouveau
                if level == 1:
                    if current_chapter and current_content_lines:
                        current_chapter.content = "\n".join(current_content_lines)
                        chapters.append(current_chapter)
                        current_content_lines = []

                    title = header_match.group(2).strip()
                    anchor = self._create_anchor(title)

                    current_chapter = ChapterInfo(
                        title=title, level=level, anchor=anchor, content=""
                    )
                    current_content_lines.append(line)
                else:
                    # H2, H3, etc. : créer des sections séparées mais pas de nouveau chapitre
                    if current_chapter and current_content_lines:
                        current_chapter.content = "\n".join(current_content_lines)
                        chapters.append(current_chapter)
                        current_content_lines = []

                    title = header_match.group(2).strip()
                    anchor = self._create_anchor(title)

                    current_chapter = ChapterInfo(
                        title=title, level=level, anchor=anchor, content=""
                    )
                    current_content_lines.append(line)
            else:
                current_content_lines.append(line)

        if current_chapter and current_content_lines:
            current_chapter.content = "\n".join(current_content_lines)
            chapters.append(current_chapter)

        logger.info(f"Parsed {len(chapters)} sections from markdown content")
        return chapters

    def extract_toc_entries(
        self, chapters: list[ChapterInfo], max_level: int = 2
    ) -> list[TOCEntry]:
        toc_entries = []

        for chapter in chapters:
            if chapter.level <= max_level:
                toc_entries.append(
                    TOCEntry(title=chapter.title, anchor=chapter.anchor, level=chapter.level)
                )

        logger.info(f"Generated {len(toc_entries)} TOC entries (max level: {max_level})")
        return toc_entries

    def generate_html_content(
        self,
        chapters: list[ChapterInfo],
        chapter_numbering: bool = False,
        chapter_numbering_style: str = "arabic",
    ) -> str:
        html_parts = []
        chapter_counter = 0

        for chapter in chapters:
            if chapter.level == 1:
                # Seuls les H1 sont de vrais chapitres avec saut de page
                chapter_counter += 1
                chapter_class = "chapter"
                if chapter_numbering:
                    chapter_class += " chapter-numbered"
                    if chapter_numbering_style == "roman":
                        chapter_class += " roman"
            else:
                # H2, H3, etc. sont des sections dans le même chapitre
                chapter_class = "section"

            chapter_html = f'<div class="{chapter_class}" id="{chapter.anchor}">'

            chapter_html += f"<h{chapter.level}>{chapter.title}</h{chapter.level}>"

            content_lines = chapter.content.split("\n")[1:]
            chapter_content = self._markdown_to_html("\n".join(content_lines))

            chapter_html += chapter_content
            chapter_html += "</div>"

            html_parts.append(chapter_html)

        return "\n".join(html_parts)

    def generate_toc_html(self, toc_entries: list[TOCEntry]) -> str:
        if not toc_entries:
            return ""

        html_parts = []

        for entry in toc_entries:
            indent_class = f"toc-level-{entry.level}"
            html_parts.append(
                f'<li class="toc-item {indent_class}">'
                f'<a href="#{entry.anchor}" class="toc-link">{entry.title}</a>'
                f"</li>"
            )

        return "\n".join(html_parts)

    def _create_anchor(self, title: str) -> str:
        anchor = re.sub(r"[^\w\s-]", "", title.lower())
        anchor = re.sub(r"[\s_-]+", "-", anchor)
        anchor = anchor.strip("-")
        return anchor or "section"

    def _to_roman(self, num: int) -> str:
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
        roman_num = ""
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman_num += syms[i]
                num -= val[i]
            i += 1
        return roman_num

    def _markdown_to_html(self, content: str) -> str:
        html = content

        html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)
        html = re.sub(r"`(.*?)`", r"<code>\1</code>", html)

        html = re.sub(r"^>\s*(.+)$", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE)

        lines = html.split("\n")
        in_list = False
        in_code_block = False
        result_lines = []

        for line in lines:
            if line.strip().startswith("```"):
                if in_code_block:
                    result_lines.append("</pre>")
                    in_code_block = False
                else:
                    result_lines.append("<pre><code>")
                    in_code_block = True
                continue

            if in_code_block:
                result_lines.append(line)
                continue

            if re.match(r"^\s*[-*+]\s+", line):
                if not in_list:
                    result_lines.append("<ul>")
                    in_list = True
                item_content = re.sub(r"^\s*[-*+]\s+", "", line)
                result_lines.append(f"<li>{item_content}</li>")
            else:
                if in_list:
                    result_lines.append("</ul>")
                    in_list = False

                if line.strip():
                    result_lines.append(f"<p>{line}</p>")
                else:
                    result_lines.append("")

        if in_list:
            result_lines.append("</ul>")
        if in_code_block:
            result_lines.append("</code></pre>")

        return "\n".join(result_lines)

    def parse_ebook_structure(self, json_content: str) -> EbookStructure:
        """Parse ebook structure from JSON content"""
        try:
            data = json.loads(json_content)

            # Créer la structure à partir du JSON
            from backoffice.domain.entities.ebook_structure import (
                EbookBackCover,
                EbookCover,
                EbookMeta,
                EbookSection,
                EbookStructure,
            )

            meta = EbookMeta(**data.get("meta", {}))
            cover = EbookCover(**data.get("cover", {}))

            sections = []
            for section_data in data.get("sections", []):
                sections.append(EbookSection(**section_data))

            back_cover_data = data.get("back_cover")
            back_cover = EbookBackCover(**back_cover_data) if back_cover_data else None

            return EbookStructure(
                meta=meta,
                cover=cover,
                toc=data.get("toc", True),
                sections=sections,
                back_cover=back_cover,
            )
        except Exception as e:
            logger.error(f"Error parsing ebook structure: {str(e)}")
            raise ValueError(f"Invalid ebook JSON structure: {str(e)}") from e

    def generate_html_from_structure(
        self,
        ebook_structure: EbookStructure,
        chapter_numbering: bool = False,
        chapter_numbering_style: str = "arabic",
    ) -> str:
        """Generate HTML content from ebook structure"""
        html_parts = []
        chapter_counter = 0

        for section in ebook_structure.sections or []:
            if section.type == "chapter":
                chapter_counter += 1
                chapter_class = "chapter"
                if chapter_numbering:
                    chapter_class += " chapter-numbered"
                    if chapter_numbering_style == "roman":
                        chapter_class += " roman"
            else:
                chapter_class = "section"

            # Créer l'ancre à partir du titre
            anchor = self._create_anchor(section.title)

            chapter_html = f'<div class="{chapter_class}" id="{anchor}">'
            chapter_html += f"<h1>{section.title}</h1>"

            # Convertir le contenu markdown en HTML
            chapter_content = self._markdown_to_html(section.content)
            chapter_html += chapter_content
            chapter_html += "</div>"

            html_parts.append(chapter_html)

        return "\n".join(html_parts)

    def generate_toc_from_structure(self, ebook_structure: EbookStructure) -> str:
        """Generate TOC HTML from ebook structure"""
        if not ebook_structure.toc:
            return ""

        html_parts = []

        for section in ebook_structure.sections or []:
            if section.type == "chapter":  # Only chapters in TOC
                anchor = self._create_anchor(section.title)
                html_parts.append(
                    f'<li class="toc-item toc-level-1">'
                    f'<a href="#{anchor}" class="toc-link">{section.title}</a>'
                    f"</li>"
                )

        return "\n".join(html_parts)
