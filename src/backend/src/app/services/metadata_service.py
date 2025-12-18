"""
Metadata Extraction Service
Extracts comprehensive metadata from various file types (images, PDFs, Office documents)
"""
from typing import Dict, Optional, Any
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MetadataService:
    """Service for extracting metadata from files"""
    
    @staticmethod
    async def extract_file_metadata(
        mime: str,
        file_bytes: bytes,
        filename: str,
        checksum: Optional[str] = None,
        upload_method: str = "web",
        upload_ip: Optional[str] = None,
        upload_user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract all metadata from file
        
        Args:
            mime: MIME type of the file
            file_bytes: File content as bytes
            filename: Original filename
            checksum: File checksum (MD5/SHA256)
            upload_method: Upload method (web, scan, api)
            upload_ip: Upload IP address (optional)
            upload_user_agent: Upload user agent (optional)
        
        Returns:
            Dictionary containing all extracted metadata
        """
        metadata = {
            "file": {
                "original_filename": filename,
                "size": len(file_bytes),
                "mime": mime,
                "checksum": checksum,
                "upload_method": upload_method,
                "upload_timestamp": datetime.utcnow().isoformat(),
                "upload_ip": upload_ip,
                "upload_user_agent": upload_user_agent
            }
        }
        
        try:
            # Extract based on MIME type
            if mime.startswith("image/"):
                exif_data = await MetadataService.extract_image_metadata(file_bytes)
                if exif_data:
                    metadata["exif"] = exif_data
            elif mime == "application/pdf":
                pdf_data = await MetadataService.extract_pdf_metadata(file_bytes)
                if pdf_data:
                    metadata["pdf"] = pdf_data
            elif mime in [
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ]:
                office_data = await MetadataService.extract_office_metadata(mime, file_bytes)
                if office_data:
                    metadata["office"] = office_data
        except Exception as e:
            logger.warning(f"Error extracting metadata for {mime}: {e}", exc_info=True)
            metadata["extraction_error"] = str(e)
        
        return metadata
    
    @staticmethod
    async def extract_image_metadata(file_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Extract EXIF and image metadata"""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS, GPSTAGS
            import json
            
            image = Image.open(BytesIO(file_bytes))
            exif_data = {}
            
            # Basic image info
            exif_data["resolution"] = {
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "mode": image.mode
            }
            
            # EXIF data
            if hasattr(image, '_getexif') and image._getexif() is not None:
                exif = image._getexif()
                exif_dict = {}
                
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except:
                            value = str(value)
                    exif_dict[tag] = value
                
                # Extract common fields
                if "Make" in exif_dict:
                    exif_data["camera_make"] = exif_dict["Make"]
                if "Model" in exif_dict:
                    exif_data["camera_model"] = exif_dict["Model"]
                if "DateTime" in exif_dict:
                    exif_data["date_taken"] = exif_dict["DateTime"]
                if "DateTimeOriginal" in exif_dict:
                    exif_data["date_taken"] = exif_dict["DateTimeOriginal"]
                if "Software" in exif_dict:
                    exif_data["software"] = exif_dict["Software"]
                if "Copyright" in exif_dict:
                    exif_data["copyright"] = exif_dict["Copyright"]
                if "Orientation" in exif_dict:
                    exif_data["orientation"] = exif_dict["Orientation"]
                
                # GPS data
                if "GPSInfo" in exif_dict:
                    gps_info = exif_dict["GPSInfo"]
                    gps_data = {}
                    for key, value in gps_info.items():
                        tag = GPSTAGS.get(key, key)
                        gps_data[tag] = value
                    
                    # Convert GPS coordinates to decimal
                    if "Latitude" in gps_data and "Longitude" in gps_data:
                        lat = gps_data["Latitude"]
                        lon = gps_data["Longitude"]
                        if isinstance(lat, tuple) and isinstance(lon, tuple):
                            # Convert from degrees/minutes/seconds to decimal
                            lat_decimal = lat[0] + lat[1]/60.0 + lat[2]/3600.0
                            lon_decimal = lon[0] + lon[1]/60.0 + lon[2]/3600.0
                            if gps_data.get("LatitudeRef") == "S":
                                lat_decimal = -lat_decimal
                            if gps_data.get("LongitudeRef") == "W":
                                lon_decimal = -lon_decimal
                            exif_data["gps"] = {
                                "lat": lat_decimal,
                                "lon": lon_decimal
                            }
                
                # Store full EXIF if needed
                exif_data["full_exif"] = exif_dict
            
            # DPI info
            if hasattr(image, 'info'):
                if 'dpi' in image.info:
                    dpi = image.info['dpi']
                    if isinstance(dpi, tuple):
                        exif_data["resolution"]["dpi_x"] = dpi[0]
                        exif_data["resolution"]["dpi_y"] = dpi[1]
            
            return exif_data if exif_data else None
            
        except Exception as e:
            logger.warning(f"Error extracting image metadata: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def extract_pdf_metadata(file_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Extract PDF metadata"""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            pdf_data = {}
            
            # Basic info
            pdf_data["page_count"] = len(doc)
            # PDF version - PyMuPDF doesn't have pdf_version() method
            # Version info is usually in the PDF header, but not directly accessible
            # We can try to get it from document properties if available
            try:
                # Try to get PDF version from document properties
                if hasattr(doc, 'PDF_VERSION'):
                    pdf_data["pdf_version"] = doc.PDF_VERSION
                else:
                    # Default to 1.4 if not available (most common)
                    pdf_data["pdf_version"] = "1.4"
            except:
                pdf_data["pdf_version"] = "1.4"  # Default fallback
            pdf_data["is_encrypted"] = doc.is_encrypted
            
            # Metadata
            metadata = doc.metadata
            if metadata:
                if metadata.get("title"):
                    pdf_data["title"] = metadata["title"]
                if metadata.get("author"):
                    pdf_data["author"] = metadata["author"]
                if metadata.get("subject"):
                    pdf_data["subject"] = metadata["subject"]
                if metadata.get("keywords"):
                    pdf_data["keywords"] = metadata["keywords"]
                if metadata.get("creator"):
                    pdf_data["creator"] = metadata["creator"]
                if metadata.get("producer"):
                    pdf_data["producer"] = metadata["producer"]
                if metadata.get("creationDate"):
                    pdf_data["creation_date"] = metadata["creationDate"]
                if metadata.get("modDate"):
                    pdf_data["modification_date"] = metadata["modDate"]
                
                # Store all metadata
                pdf_data["all_metadata"] = dict(metadata)
            
            # Custom properties (if accessible)
            # PyMuPDF doesn't directly expose custom properties, but we can try
            try:
                # Get XMP metadata if available
                xmp = doc.xmp_metadata()
                if xmp:
                    pdf_data["xmp_metadata"] = xmp
            except:
                pass
            
            doc.close()
            return pdf_data if pdf_data else None
            
        except Exception as e:
            logger.warning(f"Error extracting PDF metadata: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def extract_office_metadata(mime: str, file_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Extract Office document metadata (DOCX, XLSX, PPTX)"""
        try:
            office_data = {}
            
            if mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return await MetadataService.extract_docx_metadata(file_bytes)
            elif mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                return await MetadataService.extract_xlsx_metadata(file_bytes)
            elif mime == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                return await MetadataService.extract_pptx_metadata(file_bytes)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting Office metadata: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def extract_docx_metadata(file_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Extract DOCX metadata"""
        try:
            from docx import Document
            
            doc = Document(BytesIO(file_bytes))
            office_data = {}
            
            # Core properties
            core_props = doc.core_properties
            if core_props:
                if core_props.title:
                    office_data["title"] = core_props.title
                if core_props.author:
                    office_data["author"] = core_props.author
                if core_props.subject:
                    office_data["subject"] = core_props.subject
                if core_props.keywords:
                    office_data["keywords"] = core_props.keywords
                if core_props.created:
                    office_data["created_date"] = core_props.created.isoformat() if core_props.created else None
                if core_props.modified:
                    office_data["modified_date"] = core_props.modified.isoformat() if core_props.modified else None
                if core_props.last_modified_by:
                    office_data["last_modified_by"] = core_props.last_modified_by
                if core_props.revision:
                    office_data["revision"] = core_props.revision
            
            # Extended properties
            try:
                extended_props = doc.part.extended_properties
                if extended_props:
                    # Word count, page count, etc.
                    # These are in XML format, need to parse
                    office_data["application"] = "Microsoft Word"
            except:
                pass
            
            # Document statistics
            paragraphs = doc.paragraphs
            word_count = sum(len(p.text.split()) for p in paragraphs)
            office_data["word_count"] = word_count
            office_data["paragraph_count"] = len(paragraphs)
            
            # Custom properties (if accessible)
            try:
                custom_props = doc.part.custom_properties
                if custom_props:
                    custom_dict = {}
                    for prop in custom_props:
                        custom_dict[prop.name] = prop.value
                    if custom_dict:
                        office_data["custom_properties"] = custom_dict
            except:
                pass
            
            return office_data if office_data else None
            
        except Exception as e:
            logger.warning(f"Error extracting DOCX metadata: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def extract_xlsx_metadata(file_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Extract XLSX metadata"""
        try:
            from openpyxl import load_workbook
            
            workbook = load_workbook(BytesIO(file_bytes), data_only=True, read_only=True)
            office_data = {}
            
            # Core properties
            props = workbook.properties
            if props:
                if props.title:
                    office_data["title"] = props.title
                if props.creator:
                    office_data["author"] = props.creator
                if props.subject:
                    office_data["subject"] = props.subject
                if props.keywords:
                    office_data["keywords"] = props.keywords
                if props.created:
                    office_data["created_date"] = props.created.isoformat() if props.created else None
                if props.modified:
                    office_data["modified_date"] = props.modified.isoformat() if props.modified else None
                if props.lastModifiedBy:
                    office_data["last_modified_by"] = props.lastModifiedBy
                if props.revision:
                    office_data["revision"] = props.revision
            
            # Workbook statistics
            office_data["sheet_count"] = len(workbook.sheetnames)
            office_data["sheet_names"] = workbook.sheetnames
            
            # Count cells (approximate)
            total_cells = 0
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                total_cells += sheet.max_row * sheet.max_column
            office_data["estimated_cell_count"] = total_cells
            
            office_data["application"] = "Microsoft Excel"
            
            workbook.close()
            return office_data if office_data else None
            
        except Exception as e:
            logger.warning(f"Error extracting XLSX metadata: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def extract_pptx_metadata(file_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Extract PPTX metadata"""
        try:
            from pptx import Presentation
            
            prs = Presentation(BytesIO(file_bytes))
            office_data = {}
            
            # Core properties
            core_props = prs.core_properties
            if core_props:
                if core_props.title:
                    office_data["title"] = core_props.title
                if core_props.author:
                    office_data["author"] = core_props.author
                if core_props.subject:
                    office_data["subject"] = core_props.subject
                if core_props.keywords:
                    office_data["keywords"] = core_props.keywords
                if core_props.created:
                    office_data["created_date"] = core_props.created.isoformat() if core_props.created else None
                if core_props.modified:
                    office_data["modified_date"] = core_props.modified.isoformat() if core_props.modified else None
                if core_props.last_modified_by:
                    office_data["last_modified_by"] = core_props.last_modified_by
                if core_props.revision:
                    office_data["revision"] = core_props.revision
            
            # Presentation statistics
            office_data["slide_count"] = len(prs.slides)
            office_data["application"] = "Microsoft PowerPoint"
            
            return office_data if office_data else None
            
        except Exception as e:
            logger.warning(f"Error extracting PPTX metadata: {e}", exc_info=True)
            return None
    
    @staticmethod
    def extract_processing_metadata(
        processing_result: Dict[str, Any],
        processing_time_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Extract processing metadata from OCR/text extraction results
        
        Args:
            processing_result: Result from OCR or text extraction
            processing_time_ms: Processing time in milliseconds
        
        Returns:
            Dictionary containing processing metadata
        """
        processing_meta = {}
        
        if "provider" in processing_result:
            processing_meta["ocr_provider"] = processing_result["provider"]
        if "confidence" in processing_result:
            processing_meta["ocr_confidence"] = processing_result["confidence"]
        if "text_extraction_method" in processing_result:
            processing_meta["text_extraction_method"] = processing_result["text_extraction_method"]
        if processing_time_ms is not None:
            processing_meta["processing_time_ms"] = processing_time_ms
        
        if "error" in processing_result:
            processing_meta["errors"] = [processing_result["error"]]
        
        return processing_meta

