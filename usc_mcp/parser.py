"""
USLM XML Parser for United States Code

Parses USC XML files following the USLM schema and extracts
structured text with metadata for embedding and search.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

from lxml import etree
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

@dataclass
class USCSection:
    """Represents a section of the US Code"""
    title_num: str
    title_name: str
    chapter_num: Optional[str] = None
    chapter_name: Optional[str] = None
    section_num: str = ""
    section_name: str = ""
    section_id: str = ""
    full_citation: str = ""
    text: str = ""
    heading: str = ""
    subsections: List[Dict[str, str]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    source_credit: Optional[str] = None
    effective_date: Optional[str] = None
    amendments: List[str] = field(default_factory=list)
    cross_references: List[str] = field(default_factory=list)
    
    def get_full_text(self) -> str:
        """Get complete text including subsections"""
        parts = [self.heading, self.text]
        for subsection in self.subsections:
            parts.append(f"{subsection.get('num', '')} {subsection.get('text', '')}")
        return "\n\n".join(filter(None, parts))
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata for vector storage"""
        return {
            "title_num": self.title_num,
            "title_name": self.title_name,
            "chapter_num": self.chapter_num,
            "chapter_name": self.chapter_name,
            "section_num": self.section_num,
            "section_name": self.section_name,
            "section_id": self.section_id,
            "full_citation": self.full_citation,
            "heading": self.heading,
            "source_credit": self.source_credit,
            "effective_date": self.effective_date,
            "has_notes": len(self.notes) > 0,
            "has_amendments": len(self.amendments) > 0,
            "cross_reference_count": len(self.cross_references)
        }

class USLMParser:
    """Parser for United States Legislative Markup (USLM) XML files"""
    
    USLM_NS = "http://xml.house.gov/schemas/uslm/1.0"
    DC_NS = "http://purl.org/dc/elements/1.1/"
    
    def __init__(self):
        self.namespaces = {
            'uslm': self.USLM_NS,
            'dc': self.DC_NS
        }
        
    def parse_file(self, filepath: Path) -> List[USCSection]:
        """Parse a USC XML file and extract all sections"""
        logger.info(f"Parsing USC file: {filepath}")
        
        try:
            tree = etree.parse(str(filepath))
            root = tree.getroot()
            
            # Extract title information
            title_info = self._extract_title_info(root)
            
            # Extract all sections
            sections = []
            for section_elem in root.xpath('.//uslm:section', namespaces=self.namespaces):
                section = self._parse_section(section_elem, title_info)
                if section:
                    sections.append(section)
                    
            logger.info(f"Extracted {len(sections)} sections from {filepath}")
            return sections
            
        except Exception as e:
            logger.error(f"Error parsing {filepath}: {e}")
            raise
            
    def _extract_title_info(self, root) -> Dict[str, str]:
        """Extract title-level metadata"""
        title_info = {}
        
        # Get title number and name from metadata
        title_elem = root.find('.//dc:title', self.namespaces)
        if title_elem is not None and title_elem.text:
            # Parse "Title 26 - Internal Revenue Code" format
            match = re.match(r'Title (\d+)\s*-\s*(.+)', title_elem.text)
            if match:
                title_info['num'] = match.group(1)
                title_info['name'] = match.group(2).strip()
        
        # Fallback to identifier attribute
        if 'num' not in title_info:
            identifier = root.get('identifier', '')
            match = re.search(r'/t(\d+)', identifier)
            if match:
                title_info['num'] = match.group(1)
                
        return title_info
        
    def _parse_section(self, section_elem, title_info: Dict[str, str]) -> Optional[USCSection]:
        """Parse a single section element"""
        try:
            section = USCSection(
                title_num=title_info.get('num', ''),
                title_name=title_info.get('name', '')
            )
            
            # Get section number
            num_elem = section_elem.find('.//uslm:num', self.namespaces)
            if num_elem is not None:
                section.section_num = self._clean_text(num_elem.text)
                
            # Get section heading
            heading_elem = section_elem.find('.//uslm:heading', self.namespaces)
            if heading_elem is not None:
                section.section_name = self._clean_text(heading_elem.text)
                section.heading = f"Section {section.section_num}. {section.section_name}"
                
            # Get section ID
            section.section_id = section_elem.get('id', '')
            
            # Build full citation
            section.full_citation = f"{section.title_num} USC {section.section_num}"
            
            # Extract chapter info if available
            chapter = section_elem.xpath('ancestor::uslm:chapter[1]', namespaces=self.namespaces)
            if chapter:
                chapter_elem = chapter[0]
                chapter_num = chapter_elem.find('.//uslm:num', self.namespaces)
                chapter_heading = chapter_elem.find('.//uslm:heading', self.namespaces)
                
                if chapter_num is not None:
                    section.chapter_num = self._clean_text(chapter_num.text)
                if chapter_heading is not None:
                    section.chapter_name = self._clean_text(chapter_heading.text)
                    
            # Extract main text content
            section.text = self._extract_text_content(section_elem)
            
            # Extract subsections
            section.subsections = self._extract_subsections(section_elem)
            
            # Extract notes
            section.notes = self._extract_notes(section_elem)
            
            # Extract source credit
            source_credit = section_elem.find('.//uslm:sourceCredit', self.namespaces)
            if source_credit is not None:
                section.source_credit = self._clean_text(source_credit.text)
                
            # Extract amendments and cross-references from notes
            section.amendments = self._extract_amendments(section.notes)
            section.cross_references = self._extract_cross_references(section_elem)
            
            return section
            
        except Exception as e:
            logger.error(f"Error parsing section: {e}")
            return None
            
    def _extract_text_content(self, elem) -> str:
        """Extract all text content from an element"""
        # Get the main content, excluding subsections
        content_parts = []
        
        # Look for chapeau (introductory text)
        chapeau = elem.find('.//uslm:chapeau', self.namespaces)
        if chapeau is not None:
            content_parts.append(self._get_element_text(chapeau))
            
        # Look for main text elements
        for text_elem in elem.findall('.//uslm:text', self.namespaces):
            # Skip if it's within a subsection
            if not text_elem.xpath('ancestor::uslm:subsection', namespaces=self.namespaces):
                content_parts.append(self._get_element_text(text_elem))
                
        # Look for continuation text
        continuation = elem.find('.//uslm:continuation', self.namespaces)
        if continuation is not None:
            content_parts.append(self._get_element_text(continuation))
            
        return '\n\n'.join(filter(None, content_parts))
        
    def _extract_subsections(self, section_elem) -> List[Dict[str, str]]:
        """Extract all subsections from a section"""
        subsections = []
        
        for subsec_elem in section_elem.findall('.//uslm:subsection', self.namespaces):
            subsection = {}
            
            # Get subsection number
            num_elem = subsec_elem.find('.//uslm:num', self.namespaces)
            if num_elem is not None:
                subsection['num'] = self._clean_text(num_elem.text)
                
            # Get subsection heading (if any)
            heading_elem = subsec_elem.find('.//uslm:heading', self.namespaces)
            if heading_elem is not None:
                subsection['heading'] = self._clean_text(heading_elem.text)
                
            # Get subsection text
            subsection['text'] = self._extract_text_content(subsec_elem)
            
            # Extract nested levels (paragraphs, subparagraphs, etc.)
            nested = self._extract_nested_levels(subsec_elem)
            if nested:
                subsection['nested'] = nested
                
            subsections.append(subsection)
            
        return subsections
        
    def _extract_nested_levels(self, parent_elem) -> List[Dict[str, str]]:
        """Extract nested levels like paragraphs, subparagraphs, clauses"""
        nested = []
        
        level_tags = ['paragraph', 'subparagraph', 'clause', 'subclause', 'item']
        
        for tag in level_tags:
            for elem in parent_elem.findall(f'.//uslm:{tag}', self.namespaces):
                level = {'type': tag}
                
                # Get number
                num_elem = elem.find('.//uslm:num', self.namespaces)
                if num_elem is not None:
                    level['num'] = self._clean_text(num_elem.text)
                    
                # Get text
                level['text'] = self._extract_text_content(elem)
                
                nested.append(level)
                
        return nested
        
    def _extract_notes(self, section_elem) -> List[str]:
        """Extract all notes from a section"""
        notes = []
        
        for note_elem in section_elem.findall('.//uslm:note', self.namespaces):
            note_text = self._get_element_text(note_elem)
            if note_text:
                notes.append(note_text)
                
        return notes
        
    def _extract_amendments(self, notes: List[str]) -> List[str]:
        """Extract amendment information from notes"""
        amendments = []
        
        for note in notes:
            if 'amendment' in note.lower() or 'amended' in note.lower():
                # Extract Public Law references
                pl_matches = re.findall(r'Pub\.\s*L\.\s*\d+-\d+', note)
                amendments.extend(pl_matches)
                
        return list(set(amendments))  # Remove duplicates
        
    def _extract_cross_references(self, elem) -> List[str]:
        """Extract cross-references from an element"""
        references = []
        
        # Look for ref elements
        for ref_elem in elem.findall('.//uslm:ref', self.namespaces):
            href = ref_elem.get('href', '')
            if href:
                references.append(href)
                
        return references
        
    def _get_element_text(self, elem) -> str:
        """Get all text from an element, including nested elements"""
        if elem is None:
            return ""
            
        # Use BeautifulSoup to extract text while preserving some structure
        xml_str = etree.tostring(elem, encoding='unicode', method='xml')
        soup = BeautifulSoup(xml_str, 'xml')
        
        # Remove namespace prefixes for cleaner text
        text = soup.get_text(separator=' ', strip=True)
        
        return self._clean_text(text)
        
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
            
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove XML artifacts
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up punctuation spacing
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        text = re.sub(r'([.,;:!?])(?=[A-Za-z])', r'\1 ', text)
        
        return text.strip()
        
    def extract_chunks(self, sections: List[USCSection], max_tokens: int = 1000, 
                      overlap: int = 100) -> List[Dict[str, Any]]:
        """Extract chunks from sections for embedding"""
        chunks = []
        seen_ids = {}
        
        for section in sections:
            # Create base metadata
            base_metadata = section.get_metadata()
            
            # Get full section text
            full_text = section.get_full_text()
            
            # Create a unique ID by handling duplicates
            base_id = f"{section.title_num}-{section.section_num}"
            
            # If we've seen this ID before, append a counter
            if base_id in seen_ids:
                seen_ids[base_id] += 1
                unique_id = f"{base_id}-{seen_ids[base_id]}"
            else:
                seen_ids[base_id] = 0
                unique_id = base_id
            
            # For now, treat each section as a chunk
            # In production, would split large sections
            chunk = {
                'id': unique_id,
                'text': full_text,
                'metadata': base_metadata
            }
            
            chunks.append(chunk)
            
        return chunks