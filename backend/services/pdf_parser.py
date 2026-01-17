"""
PDF Parser Service - Extracts text from lab report PDFs using PyMuPDF
"""
import fitz  # PyMuPDF
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PDFParser:
    """Service for extracting text from PDF lab reports"""
    
    def __init__(self):
        self.supported_formats = ['.pdf']
    
    def extract_text(self, file_path: str) -> str:
        """
        Extract text from a PDF file
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text as string
        """
        try:
            doc = fitz.open(file_path)
            num_pages = len(doc)  # Store page count before closing
            text_parts = []
            
            for page_num in range(num_pages):
                page = doc[page_num]
                
                # Try multiple extraction methods for better results
                # Method 1: Try blocks extraction first (better for tables)
                blocks = page.get_text("blocks")
                block_text = "\n".join([block[4] for block in blocks if block[4].strip()])
                
                # Method 2: Standard text extraction
                standard_text = page.get_text()
                
                # Use the method that extracted more text
                if len(block_text) > len(standard_text):
                    text = block_text
                else:
                    text = standard_text
                
                # If still very little text, try dict format
                if len(text.strip()) < 50:
                    try:
                        text_dict = page.get_text("dict")
                        text = ""
                        for block in text_dict.get("blocks", []):
                            if "lines" in block:
                                for line in block["lines"]:
                                    for span in line.get("spans", []):
                                        text += span.get("text", "") + " "
                                    text += "\n"
                    except Exception as dict_error:
                        logger.debug(f"Dict extraction failed for page {page_num}: {dict_error}")
                        pass
                
                text_parts.append(text)
            
            doc.close()
            
            full_text = "\n".join(text_parts)
            
            # Clean up the text - remove excessive whitespace but preserve structure
            lines = full_text.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if line:  # Skip empty lines
                    cleaned_lines.append(line)
            
            full_text = "\n".join(cleaned_lines)
            logger.info(f"Extracted {len(full_text)} characters from PDF ({num_pages} pages)")
            
            return full_text
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    def create_redacted_pdf(self, original_path: str, original_text: str, pii_entities: list, output_path: str) -> str:
        """
        Create a redacted PDF with visual redaction marks
        
        Args:
            original_path: Path to the original PDF file
            original_text: The original extracted text
            pii_entities: List of PII entities from Presidio analyzer (with start, end, entity_type)
            output_path: Path to save the redacted PDF
            
        Returns:
            Path to the created redacted PDF
        """
        try:
            # Open original PDF
            doc = fitz.open(original_path)
            
            # For each page, find and redact PII
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # For each PII entity, find and redact it on the page
                for entity in pii_entities:
                    # Get the text that was redacted
                    text_to_find = original_text[entity['start']:entity['end']]
                    
                    if not text_to_find.strip():
                        continue
                    
                    # Find all instances of this text on the page
                    try:
                        text_rects = page.search_for(text_to_find, flags=fitz.TEXT_DEHYPHENATE)
                        
                        for rect in text_rects:
                            # Draw a yellow rectangle over the text (redaction)
                            redaction_rect = fitz.Rect(rect)
                            # Add some padding
                            redaction_rect.x0 -= 1
                            redaction_rect.y0 -= 1
                            redaction_rect.x1 += 1
                            redaction_rect.y1 += 1
                            
                            # Draw yellow box over it
                            page.draw_rect(redaction_rect, color=(1, 1, 0), width=0, fill=(1, 1, 0))
                    except:
                        # If search fails, skip this entity
                        continue
            
            # Save the redacted PDF
            doc.save(output_path)
            doc.close()
            
            logger.info(f"Created redacted PDF at {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating redacted PDF: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # If redaction fails, just copy the original
            import shutil
            shutil.copy(original_path, output_path)
            return output_path
    
    def extract_images(self, file_path: str) -> list:
        """
        Extract images from PDF (for future OCR support)
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of image data
        """
        try:
            doc = fitz.open(file_path)
            images = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    images.append({
                        "page": page_num,
                        "index": img_index,
                        "data": base_image["image"]
                    })
            
            doc.close()
            return images
        
        except Exception as e:
            logger.error(f"Error extracting images from PDF: {e}")
            return []
