from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import validate_resume_file
from .services.resume_parser import extract_text_from_resume


class ResumeValidationTests(TestCase):
    def test_pdf_extension_is_accepted(self):
        f = SimpleUploadedFile('resume.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        validate_resume_file(f)  # should not raise

    def test_txt_extension_is_rejected(self):
        f = SimpleUploadedFile('resume.txt', b'plain text', content_type='text/plain')
        with self.assertRaises(ValidationError):
            validate_resume_file(f)


class ResumeExtractionTests(TestCase):
    def test_unreadable_file_returns_empty_string_not_an_exception(self):
        # A corrupted/missing file should degrade gracefully (Section 27),
        # never raise an exception up into the view.
        result = extract_text_from_resume('/tmp/this_file_does_not_exist.pdf')
        self.assertEqual(result, '')
