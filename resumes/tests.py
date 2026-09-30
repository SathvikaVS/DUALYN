from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import validate_resume_file
from .services.resume_parser import extract_text_from_resume
from .services.skill_analyzer import parse_ai_response, validate_against_catalog
from skills.models import Skill


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


class AIResponseParsingTests(TestCase):
    def test_plain_json_array_is_parsed(self):
        result = parse_ai_response('["Python", "Django"]')
        self.assertEqual(result, ["Python", "Django"])

    def test_json_wrapped_in_markdown_fence_is_still_parsed(self):
        result = parse_ai_response('```json\n["Python", "SQL"]\n```')
        self.assertEqual(result, ["Python", "SQL"])

    def test_garbage_response_returns_empty_list_not_an_exception(self):
        result = parse_ai_response("Sorry, I can't help with that.")
        self.assertEqual(result, [])

    def test_non_list_json_returns_empty_list(self):
        result = parse_ai_response('{"skill": "Python"}')
        self.assertEqual(result, [])


class SkillCatalogValidationTests(TestCase):
    def setUp(self):
        Skill.objects.create(name='Python')
        Skill.objects.create(name='Django')

    def test_matching_skill_names_are_accepted(self):
        result = validate_against_catalog(['Python', 'Django'])
        names = {s.name for s in result}
        self.assertEqual(names, {'Python', 'Django'})

    def test_case_and_whitespace_differences_still_match(self):
        result = validate_against_catalog(['  python ', 'DJANGO'])
        names = {s.name for s in result}
        self.assertEqual(names, {'Python', 'Django'})

    def test_a_skill_not_in_the_catalog_is_silently_dropped(self):
        result = validate_against_catalog(['Python', 'Kubernetes'])
        names = {s.name for s in result}
        self.assertEqual(names, {'Python'})
        self.assertFalse(Skill.objects.filter(name='Kubernetes').exists())