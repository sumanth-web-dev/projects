"""
Intelligent form filler for automated form completion.

This module provides functionality for detecting and filling out form fields
intelligently based on field types and user profile data.
"""
import os
import re
import logging
import time
import random
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from playwright.sync_api import Page, ElementHandle, TimeoutError

from automation.playwright_engine.interaction_handler import interaction_handler
from automation.form_response_generator import form_response_generator, FormField
from services.ai_service import JobContext

# Set up logging
logger = logging.getLogger(__name__)


class FormFiller:
    """Intelligent form filler for automated form completion."""
    
    # Common field types
    TEXT = "text"
    EMAIL = "email"
    PASSWORD = "password"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    FILE = "file"
    DATE = "date"
    TEL = "tel"
    NUMBER = "number"
    URL = "url"
    BUTTON = "button"
    SUBMIT = "submit"
    
    def __init__(self, app=None):
        """Initialize FormFiller instance.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self._upload_folder = "uploads"
        self._field_mapping = self._load_field_mapping()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the form filler with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self._upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    
    def detect_form_fields(self, page: Page, form_selector: Optional[str] = None) -> List[FormField]:
        """Detect form fields on a page.
        
        Args:
            page: Playwright page
            form_selector: Optional selector for a specific form
            
        Returns:
            List[FormField]: Detected form fields
        """
        try:
            # Define the base selector
            base_selector = f"{form_selector} " if form_selector else ""
            
            # Get all input elements
            input_selector = f"{base_selector}input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='reset'])"
            textarea_selector = f"{base_selector}textarea"
            select_selector = f"{base_selector}select"
            
            # Get all form elements
            inputs = page.query_selector_all(input_selector)
            textareas = page.query_selector_all(textarea_selector)
            selects = page.query_selector_all(select_selector)
            
            # Process all elements
            form_fields = []
            
            # Process input elements
            for input_element in inputs:
                field = self._process_input_element(page, input_element)
                if field:
                    form_fields.append(field)
            
            # Process textarea elements
            for textarea in textareas:
                field = self._process_textarea_element(page, textarea)
                if field:
                    form_fields.append(field)
            
            # Process select elements
            for select in selects:
                field = self._process_select_element(page, select)
                if field:
                    form_fields.append(field)
            
            logger.info(f"Detected {len(form_fields)} form fields")
            return form_fields
            
        except Exception as e:
            logger.error(f"Error detecting form fields: {str(e)}")
            return []
    
    def fill_form(self, page: Page, form_fields: List[FormField], 
                 user_profile: Dict, job_context: Optional[JobContext] = None,
                 submit_selector: Optional[str] = None) -> bool:
        """Fill out a form with user profile data.
        
        Args:
            page: Playwright page
            form_fields: List of form fields to fill
            user_profile: User profile data
            job_context: Optional job context for AI-powered responses
            submit_selector: Optional selector for the submit button
            
        Returns:
            bool: True if form was filled successfully, False otherwise
        """
        try:
            success_count = 0
            
            # Fill each field
            for field in form_fields:
                if self._fill_field(page, field, user_profile, job_context):
                    success_count += 1
            
            # Submit the form if requested
            if submit_selector:
                # Small delay before submitting
                time.sleep(random.uniform(0.5, 1.5))
                
                # Click the submit button
                interaction_handler.human_click(page, submit_selector)
                
                # Wait for navigation
                interaction_handler.wait_for_navigation(page)
            
            # Return success if all required fields were filled
            required_fields = [f for f in form_fields if f.required]
            return success_count >= len(required_fields)
            
        except Exception as e:
            logger.error(f"Error filling form: {str(e)}")
            return False
    
    def upload_file(self, page: Page, selector: str, file_path: str) -> bool:
        """Upload a file to a file input.
        
        Args:
            page: Playwright page
            selector: File input selector
            file_path: Path to the file to upload
            
        Returns:
            bool: True if file was uploaded successfully, False otherwise
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
            
            # Set file input value
            page.set_input_files(selector, file_path)
            
            # Small delay after upload
            time.sleep(random.uniform(0.5, 1.0))
            
            return True
            
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return False
    
    def _process_input_element(self, page: Page, element: ElementHandle) -> Optional[FormField]:
        """Process an input element and create a FormField.
        
        Args:
            page: Playwright page
            element: Input element handle
            
        Returns:
            Optional[FormField]: Created form field or None if invalid
        """
        try:
            # Get element attributes
            element_id = element.get_attribute('id') or ''
            element_name = element.get_attribute('name') or ''
            element_type = element.get_attribute('type') or 'text'
            element_required = element.get_attribute('required') is not None
            element_placeholder = element.get_attribute('placeholder') or ''
            element_max_length = element.get_attribute('maxlength')
            
            # Get field ID (prefer ID, fallback to name)
            field_id = element_id or element_name
            if not field_id:
                return None
            
            # Get field label
            label = self._find_label_for_element(page, element_id, element_name)
            
            # For radio and checkbox, get the label text as a fallback
            if (element_type == 'radio' or element_type == 'checkbox') and not label:
                # Try to get text from parent or next sibling
                label = self._get_associated_text(page, element)
            
            # If still no label, use placeholder or ID/name
            if not label:
                label = element_placeholder or field_id
            
            # Convert maxlength to int if present
            max_length = None
            if element_max_length:
                try:
                    max_length = int(element_max_length)
                except ValueError:
                    pass
            
            # Handle different input types
            if element_type == 'radio':
                # Get all radio buttons with the same name
                options = self._get_radio_options(page, element_name)
                
                return FormField(
                    field_id=field_id,
                    field_type=FormField.RADIO,
                    label=label,
                    options=options,
                    required=element_required
                )
                
            elif element_type == 'checkbox':
                return FormField(
                    field_id=field_id,
                    field_type=FormField.CHECKBOX,
                    label=label,
                    required=element_required
                )
                
            elif element_type == 'file':
                return FormField(
                    field_id=field_id,
                    field_type=FormField.FILE,
                    label=label,
                    required=element_required
                )
                
            else:  # text, email, password, tel, number, url, date
                return FormField(
                    field_id=field_id,
                    field_type=FormField.TEXT,
                    label=label,
                    required=element_required,
                    placeholder=element_placeholder,
                    max_length=max_length
                )
                
        except Exception as e:
            logger.error(f"Error processing input element: {str(e)}")
            return None
    
    def _process_textarea_element(self, page: Page, element: ElementHandle) -> Optional[FormField]:
        """Process a textarea element and create a FormField.
        
        Args:
            page: Playwright page
            element: Textarea element handle
            
        Returns:
            Optional[FormField]: Created form field or None if invalid
        """
        try:
            # Get element attributes
            element_id = element.get_attribute('id') or ''
            element_name = element.get_attribute('name') or ''
            element_required = element.get_attribute('required') is not None
            element_placeholder = element.get_attribute('placeholder') or ''
            element_max_length = element.get_attribute('maxlength')
            
            # Get field ID (prefer ID, fallback to name)
            field_id = element_id or element_name
            if not field_id:
                return None
            
            # Get field label
            label = self._find_label_for_element(page, element_id, element_name)
            
            # If no label, use placeholder or ID/name
            if not label:
                label = element_placeholder or field_id
            
            # Convert maxlength to int if present
            max_length = None
            if element_max_length:
                try:
                    max_length = int(element_max_length)
                except ValueError:
                    pass
            
            return FormField(
                field_id=field_id,
                field_type=FormField.TEXTAREA,
                label=label,
                required=element_required,
                placeholder=element_placeholder,
                max_length=max_length
            )
            
        except Exception as e:
            logger.error(f"Error processing textarea element: {str(e)}")
            return None
    
    def _process_select_element(self, page: Page, element: ElementHandle) -> Optional[FormField]:
        """Process a select element and create a FormField.
        
        Args:
            page: Playwright page
            element: Select element handle
            
        Returns:
            Optional[FormField]: Created form field or None if invalid
        """
        try:
            # Get element attributes
            element_id = element.get_attribute('id') or ''
            element_name = element.get_attribute('name') or ''
            element_required = element.get_attribute('required') is not None
            
            # Get field ID (prefer ID, fallback to name)
            field_id = element_id or element_name
            if not field_id:
                return None
            
            # Get field label
            label = self._find_label_for_element(page, element_id, element_name)
            
            # If no label, use ID/name
            if not label:
                label = field_id
            
            # Get options
            options = self._get_select_options(page, element)
            
            return FormField(
                field_id=field_id,
                field_type=FormField.SELECT,
                label=label,
                options=options,
                required=element_required
            )
            
        except Exception as e:
            logger.error(f"Error processing select element: {str(e)}")
            return None
    
    def _find_label_for_element(self, page: Page, element_id: str, element_name: str) -> str:
        """Find the label text for an element.
        
        Args:
            page: Playwright page
            element_id: Element ID
            element_name: Element name
            
        Returns:
            str: Label text or empty string if not found
        """
        label_text = ""
        
        try:
            # Try to find label by for attribute
            if element_id:
                label_selector = f"label[for='{element_id}']"
                label_element = page.query_selector(label_selector)
                if label_element:
                    label_text = label_element.inner_text().strip()
                    if label_text:
                        return label_text
            
            # Try to find label by containing the input
            if element_name:
                # This is a complex selector that might not work in all cases
                label_selector = f"label:has(input[name='{element_name}'])"
                try:
                    label_element = page.query_selector(label_selector)
                    if label_element:
                        label_text = label_element.inner_text().strip()
                        if label_text:
                            return label_text
                except:
                    pass
            
            # Try to find preceding text node or element
            if element_id:
                # Look for elements that might be labels
                preceding_selector = f"#{element_id} ~ label, #{element_id} ~ div, #{element_id} ~ span, #{element_id} ~ p"
                preceding_elements = page.query_selector_all(preceding_selector)
                
                for elem in preceding_elements:
                    text = elem.inner_text().strip()
                    if text:
                        return text
            
            return label_text
            
        except Exception as e:
            logger.debug(f"Error finding label: {str(e)}")
            return label_text
    
    def _get_associated_text(self, page: Page, element: ElementHandle) -> str:
        """Get text associated with an element (for radio/checkbox).
        
        Args:
            page: Playwright page
            element: Element handle
            
        Returns:
            str: Associated text or empty string if not found
        """
        try:
            # Try to get parent element
            parent_js = """(element) => {
                const parent = element.parentElement;
                if (parent) {
                    return parent.innerText.trim();
                }
                return '';
            }"""
            
            parent_text = element.evaluate(parent_js)
            if parent_text:
                return parent_text
            
            # Try to get next sibling text
            sibling_js = """(element) => {
                let sibling = element.nextSibling;
                while (sibling) {
                    if (sibling.nodeType === 3 && sibling.textContent.trim()) {
                        return sibling.textContent.trim();
                    }
                    if (sibling.nodeType === 1) {
                        return sibling.innerText.trim();
                    }
                    sibling = sibling.nextSibling;
                }
                return '';
            }"""
            
            sibling_text = element.evaluate(sibling_js)
            if sibling_text:
                return sibling_text
            
            return ""
            
        except Exception as e:
            logger.debug(f"Error getting associated text: {str(e)}")
            return ""
    
    def _get_radio_options(self, page: Page, name: str) -> List[str]:
        """Get options for radio buttons with the same name.
        
        Args:
            page: Playwright page
            name: Radio button name
            
        Returns:
            List[str]: Radio button options
        """
        options = []
        
        try:
            # Get all radio buttons with the same name
            radio_selector = f"input[type='radio'][name='{name}']"
            radio_buttons = page.query_selector_all(radio_selector)
            
            for radio in radio_buttons:
                # Try to get the value
                value = radio.get_attribute('value') or ''
                
                # Try to get associated label or text
                label = self._get_associated_text(page, radio)
                
                # Use label or value
                option_text = label or value
                if option_text:
                    options.append(option_text)
            
            return options
            
        except Exception as e:
            logger.error(f"Error getting radio options: {str(e)}")
            return options
    
    def _get_select_options(self, page: Page, select_element: ElementHandle) -> List[str]:
        """Get options for a select element.
        
        Args:
            page: Playwright page
            select_element: Select element handle
            
        Returns:
            List[str]: Select options
        """
        options = []
        
        try:
            # Get all option elements
            options_js = """(select) => {
                return Array.from(select.options)
                    .filter(option => option.value && !option.disabled)
                    .map(option => option.text.trim() || option.value);
            }"""
            
            options = select_element.evaluate(options_js)
            return options
            
        except Exception as e:
            logger.error(f"Error getting select options: {str(e)}")
            return options
    
    def _fill_field(self, page: Page, field: FormField, 
                  user_profile: Dict, job_context: Optional[JobContext] = None) -> bool:
        """Fill a single form field.
        
        Args:
            page: Playwright page
            field: Form field to fill
            user_profile: User profile data
            job_context: Optional job context for AI-powered responses
            
        Returns:
            bool: True if field was filled successfully, False otherwise
        """
        try:
            # Skip non-required fields randomly (20% chance)
            if not field.required and random.random() < 0.2:
                logger.debug(f"Skipping non-required field: {field.field_id}")
                return True
            
            # Try to map field to user profile data
            user_data = form_response_generator.map_user_data_to_field(field, user_profile)
            
            # If no mapping found and job context available, use AI to generate response
            if user_data is None and job_context is not None:
                response, quality = form_response_generator.generate_field_response(field, job_context, user_profile)
                user_data = response
            
            # If still no data, use fallback
            if user_data is None:
                user_data = self._get_fallback_value(field)
            
            # Fill the field based on its type
            if field.field_type == FormField.TEXT:
                return interaction_handler.human_type(page, f"#{field.field_id}, [name='{field.field_id}']", str(user_data))
                
            elif field.field_type == FormField.TEXTAREA:
                return interaction_handler.human_type(page, f"#{field.field_id}, [name='{field.field_id}']", str(user_data))
                
            elif field.field_type == FormField.SELECT:
                if isinstance(user_data, str) and user_data in field.options:
                    return interaction_handler.human_select_option(page, f"#{field.field_id}, [name='{field.field_id}']", label=user_data)
                elif field.options:
                    # Select first option if no match
                    return interaction_handler.human_select_option(page, f"#{field.field_id}, [name='{field.field_id}']", label=field.options[0])
                return False
                
            elif field.field_type == FormField.RADIO:
                if isinstance(user_data, str) and user_data in field.options:
                    # Find the radio button with matching label or value
                    radio_selector = f"input[type='radio'][name='{field.field_id}'][value='{user_data}']"
                    if page.query_selector(radio_selector):
                        return interaction_handler.human_click(page, radio_selector)
                    
                    # Try to find by associated label
                    for option in field.options:
                        if option == user_data:
                            # This is complex and might not work in all cases
                            label_selector = f"label:has-text('{option}')"
                            if page.query_selector(label_selector):
                                return interaction_handler.human_click(page, label_selector)
                
                # Select first option if no match and required
                if field.required and field.options:
                    radio_selector = f"input[type='radio'][name='{field.field_id}']:first-of-type"
                    return interaction_handler.human_click(page, radio_selector)
                
                return False
                
            elif field.field_type == FormField.CHECKBOX:
                # Convert to boolean
                check_value = False
                if isinstance(user_data, bool):
                    check_value = user_data
                elif isinstance(user_data, str):
                    check_value = user_data.lower() in ('yes', 'true', '1', 'y')
                
                checkbox_selector = f"#{field.field_id}, [name='{field.field_id}']"
                return interaction_handler.human_check_checkbox(page, checkbox_selector, check_value)
                
            elif field.field_type == FormField.FILE:
                # File uploads need special handling
                if isinstance(user_data, str) and os.path.exists(user_data):
                    return self.upload_file(page, f"#{field.field_id}, [name='{field.field_id}']", user_data)
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error filling field {field.field_id}: {str(e)}")
            return False
    
    def _get_fallback_value(self, field: FormField) -> Any:
        """Get a fallback value for a field.
        
        Args:
            field: Form field
            
        Returns:
            Any: Fallback value
        """
        field_id_lower = field.field_id.lower()
        label_lower = field.label.lower()
        
        # Check for common field types
        if field.field_type == FormField.TEXT:
            # Name fields
            if any(term in field_id_lower or term in label_lower for term in ['first_name', 'firstname', 'fname']):
                return "John"
            
            if any(term in field_id_lower or term in label_lower for term in ['last_name', 'lastname', 'lname']):
                return "Doe"
            
            if any(term in field_id_lower or term in label_lower for term in ['full_name', 'fullname', 'name']):
                return "John Doe"
            
            # Contact information
            if any(term in field_id_lower or term in label_lower for term in ['email', 'e-mail']):
                return "john.doe@example.com"
            
            if any(term in field_id_lower or term in label_lower for term in ['phone', 'telephone', 'mobile']):
                return "555-123-4567"
            
            # Address fields
            if any(term in field_id_lower or term in label_lower for term in ['address', 'street']):
                return "123 Main St"
            
            if any(term in field_id_lower or term in label_lower for term in ['city', 'town']):
                return "Anytown"
            
            if any(term in field_id_lower or term in label_lower for term in ['state', 'province']):
                return "CA"
            
            if any(term in field_id_lower or term in label_lower for term in ['zip', 'postal', 'postcode']):
                return "12345"
            
            if any(term in field_id_lower or term in label_lower for term in ['country']):
                return "USA"
            
            # Default text
            return "N/A"
            
        elif field.field_type == FormField.TEXTAREA:
            # Default textarea
            return "Please see my attached resume for details."
            
        elif field.field_type == FormField.SELECT:
            # Return first option if available
            if field.options:
                return field.options[0]
            return ""
            
        elif field.field_type == FormField.RADIO:
            # Return first option if available
            if field.options:
                return field.options[0]
            return ""
            
        elif field.field_type == FormField.CHECKBOX:
            # Default to checked for required, unchecked for optional
            return field.required
            
        elif field.field_type == FormField.FILE:
            # No good fallback for file uploads
            return ""
        
        return ""
    
    def _load_field_mapping(self) -> Dict[str, Dict[str, str]]:
        """Load field mapping configuration.
        
        Returns:
            Dict[str, Dict[str, str]]: Field mapping configuration
        """
        # Default field mappings
        return {
            "personal": {
                "first_name": ["first_name", "firstname", "fname", "givenname"],
                "last_name": ["last_name", "lastname", "lname", "surname"],
                "full_name": ["full_name", "fullname", "name"],
                "email": ["email", "e-mail", "emailaddress"],
                "phone": ["phone", "telephone", "mobile", "cell", "phonenumber"],
                "address": ["address", "street", "streetaddress"],
                "city": ["city", "town"],
                "state": ["state", "province", "region"],
                "zip_code": ["zip", "zipcode", "postal", "postalcode"],
                "country": ["country", "nation"]
            },
            "education": {
                "degree": ["degree", "education", "qualification"],
                "field": ["field", "major", "subject"],
                "institution": ["institution", "university", "college", "school"]
            },
            "experience": {
                "years": ["years", "experience", "workexperience"],
                "position": ["position", "title", "jobtitle"],
                "company": ["company", "employer", "organization"]
            }
        }


# Create a singleton instance
form_filler = FormFiller()