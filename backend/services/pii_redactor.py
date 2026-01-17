"""
PII Redaction Service - Uses Microsoft Presidio to detect and redact PII
HIPAA-conscious de-identification before sending data to LLMs
"""
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import logging

logger = logging.getLogger(__name__)


class PIIRedactor:
    """
    Service for detecting and redacting PII/PHI from lab reports
    Uses Microsoft Presidio for local, on-premise redaction
    """
    
    def __init__(self):
        """Initialize Presidio analyzer and anonymizer engines"""
        try:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            
            # Configure anonymization operators
            self.operators = {
                "PERSON": OperatorConfig("replace", {"new_value": "[PATIENT_NAME]"}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
                "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
                "US_SSN": OperatorConfig("replace", {"new_value": "[SSN]"}),
                "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[CARD]"}),
                "DATE_TIME": OperatorConfig("replace", {"new_value": "[DATE]"}),
                "LOCATION": OperatorConfig("replace", {"new_value": "[LOCATION]"}),
                "IP_ADDRESS": OperatorConfig("replace", {"new_value": "[IP]"}),
                "US_PASSPORT": OperatorConfig("replace", {"new_value": "[PASSPORT]"}),
                "US_DRIVER_LICENSE": OperatorConfig("replace", {"new_value": "[DL]"}),
            }
            
            logger.info("PII Redactor initialized successfully")
        
        except Exception as e:
            logger.error(f"Error initializing PII Redactor: {e}")
            raise
    
    def redact(self, text: str) -> str:
        """
        Detect and redact PII from text
        
        Args:
            text: Input text that may contain PII/PHI
            
        Returns:
            Text with PII redacted
        """
        try:
            # Analyze text for PII entities
            results = self.analyzer.analyze(
                text=text,
                language='en',
                entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", 
                         "CREDIT_CARD", "DATE_TIME", "LOCATION", "IP_ADDRESS",
                         "US_PASSPORT", "US_DRIVER_LICENSE"]
            )
            
            if not results:
                logger.info("No PII detected in text")
                return text
            
            # Anonymize the detected entities
            anonymized = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators=self.operators
            )
            
            redacted_text = anonymized.text
            logger.info(f"Redacted {len(results)} PII entities from text")
            
            return redacted_text
        
        except Exception as e:
            logger.error(f"Error redacting PII: {e}")
            # Return original text if redaction fails (fail-safe)
            return text
    
    def get_detected_entities(self, text: str) -> list:
        """
        Get list of detected PII entities without redacting
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of detected entities with their positions
        """
        try:
            results = self.analyzer.analyze(
                text=text,
                language='en',
                entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN",
                         "CREDIT_CARD", "DATE_TIME", "LOCATION"]
            )
            
            return [
                {
                    "entity_type": result.entity_type,
                    "start": result.start,
                    "end": result.end,
                    "score": result.score
                }
                for result in results
            ]
        
        except Exception as e:
            logger.error(f"Error detecting entities: {e}")
            return []
