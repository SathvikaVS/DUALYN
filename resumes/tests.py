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


class CompetencyExtractionTests(TestCase):
    def setUp(self):
        from jobs.services.role_profiles import sync_role_profiles_to_db
        sync_role_profiles_to_db()

    def test_extracts_technical_skills_tools_databases_and_project_skills(self):
        resume_text = """
        TECHNICAL SKILLS
        Languages: Python, Java
        Databases: MySQL, PostgreSQL
        Tools: Git, GitHub, VS Code, Postman
        Frameworks: Django, FastAPI
        PROJECTS
        Online Bookstore Web App:
        - Built with Python, Django, MySQL, HTML, and CSS.
        - Applied Object-Oriented Programming and automated testing with pytest.
        """
        from .services.skill_analyzer import extract_resume_skills
        skills = extract_resume_skills(resume_text)
        skill_names = {s.name for s in skills}

        # Check technical skills
        self.assertIn('Python', skill_names)
        self.assertIn('Java', skill_names)
        # Check frameworks
        self.assertIn('Django', skill_names)
        self.assertIn('FastAPI', skill_names)
        # Check databases
        self.assertIn('MySQL', skill_names)
        self.assertIn('PostgreSQL', skill_names)
        # Check tools
        self.assertIn('Git', skill_names)
        self.assertIn('GitHub', skill_names)
        self.assertIn('VS Code', skill_names)
        self.assertIn('Postman', skill_names)
        # Check project competencies
        self.assertIn('HTML', skill_names)
        self.assertIn('CSS', skill_names)
        self.assertNotIn('HTML & CSS', skill_names, "Should avoid duplicate overlapping HTML & CSS chip")
        self.assertIn('Object-Oriented Programming', skill_names)
        self.assertIn('Testing', skill_names)

    def test_does_not_invent_skills_not_in_resume(self):
        resume_text = "Skills: Python, Django, SQL."
        from .services.skill_analyzer import extract_resume_skills
        skills = extract_resume_skills(resume_text)
        skill_names = {s.name for s in skills}

        self.assertIn('Python', skill_names)
        self.assertIn('Django', skill_names)
        self.assertIn('SQL', skill_names)

        # Ensure unmentioned skills are NOT invented
        for unsupported in ['C++', 'Ruby', 'Rust', 'Go', 'Kubernetes', 'MongoDB', 'React', 'Angular']:
            self.assertNotIn(unsupported, skill_names, f"{unsupported} should not be invented")

    def test_grounding_rejects_hallucinated_candidate(self):
        from .services.skill_analyzer import _is_candidate_supported_by_text
        lower_text = "built backend services using python and django."

        # Supported skills
        self.assertTrue(_is_candidate_supported_by_text('Python', lower_text))
        self.assertTrue(_is_candidate_supported_by_text('Django', lower_text))

        # Hallucinated skills not in text
        self.assertFalse(_is_candidate_supported_by_text('Kubernetes', lower_text))
        self.assertFalse(_is_candidate_supported_by_text('Docker', lower_text))
        self.assertFalse(_is_candidate_supported_by_text('MongoDB', lower_text))

    def test_debugging_does_not_infer_testing(self):
        """Requirement 4: Do not automatically infer Testing just because Debugging is mentioned."""
        resume_text = """
        TECHNICAL SKILLS
        Programming: Python, SQL
        Concepts: Object-Oriented Programming, debugging, code troubleshooting
        """
        from .services.skill_analyzer import extract_resume_skills_with_evidence
        skills, evidence = extract_resume_skills_with_evidence(resume_text)
        names = {s.name for s in skills}

        self.assertIn('Debugging', names)
        self.assertNotIn('Testing', names, "Testing should not be inferred when only debugging is mentioned")
        self.assertNotIn('Testing & Debugging', names, "Combined Testing & Debugging should not be extracted without testing")
        self.assertEqual(evidence['Debugging']['section'], 'Technical Skills')
        self.assertIn('debugging', evidence['Debugging']['sentence'].lower())

    def test_duplicate_aliases_and_overlapping_skills_avoided(self):
        """Requirement 2: HTML5 maps to HTML, CSS3 to CSS, avoiding duplicate HTML & CSS."""
        resume_text = """
        TECHNICAL SKILLS
        Web Technologies: HTML5, CSS3, responsive design basics
        Tools: Visual Studio Code, Git, GitHub
        """
        from .services.skill_analyzer import extract_resume_skills
        skills = extract_resume_skills(resume_text)
        names = {s.name for s in skills}

        self.assertIn('HTML', names)
        self.assertIn('CSS', names)
        self.assertIn('VS Code', names)
        self.assertIn('Git', names)
        self.assertIn('GitHub', names)
        self.assertNotIn('HTML & CSS', names, "Duplicate compound HTML & CSS should be suppressed")

    def test_traceability_evidence_on_all_detected_skills(self):
        """Requirement 6: Every detected competency must be traceable to exact sentence/section."""
        resume_text = """
        TECHNICAL SKILLS
        Programming: Python, SQL
        Concepts: CRUD operations, Object-Oriented Programming
        EDUCATION
        Relevant coursework: Database Management Systems, Software Engineering
        """
        from .services.skill_analyzer import extract_resume_skills_with_evidence
        skills, evidence = extract_resume_skills_with_evidence(resume_text)

        self.assertTrue(len(skills) >= 5)
        for skill in skills:
            self.assertIn(skill.name, evidence, f"Skill {skill.name} must have evidence")
            ev = evidence[skill.name]
            self.assertIn('section', ev)
            self.assertIn('sentence', ev)
            self.assertTrue(bool(ev['sentence']), f"Skill {skill.name} must have a non-empty sentence")
            self.assertFalse(ev.get('is_inferred', False), "Explicit skills must have is_inferred=False")
            self.assertEqual(ev.get('evidence_type'), 'explicit')

    def test_empty_and_whitespace_resumes(self):
        """Requirement 9: Empty resumes and whitespace-only text must degrade gracefully."""
        from .services.skill_analyzer import extract_resume_skills_with_evidence, extract_resume_skills
        for empty_val in ['', '   \n\t  ', None]:
            skills, evidence = extract_resume_skills_with_evidence(empty_val)
            self.assertEqual(skills, [])
            self.assertEqual(evidence, {})
            self.assertEqual(extract_resume_skills(empty_val), [])

    def test_surya_demo_resume_extraction(self):
        """Verify complete extraction on Surya's demo resume file if present."""
        import os
        from resumes.services.resume_parser import extract_text_from_resume
        from .services.skill_analyzer import extract_resume_skills_with_evidence

        resume_path = os.path.join('media', 'resumes', '2026', '10', 'Surya_Demo_Resume.docx')
        if not os.path.exists(resume_path):
            self.skipTest(f"Surya demo resume not found at {resume_path}")

        extracted_text = extract_text_from_resume(resume_path)
        self.assertTrue(bool(extracted_text))

        skills, evidence = extract_resume_skills_with_evidence(extracted_text)
        skill_names = {s.name for s in skills}

        expected_skills = {
            'Python', 'Django', 'SQL', 'MySQL', 'SQLite',
            'Git', 'GitHub', 'VS Code', 'HTML', 'CSS',
            'Object-Oriented Programming', 'CRUD Operations',
            'Debugging', 'Database Management Systems (DBMS)',
            'Web Development', 'Software Engineering'
        }

        self.assertEqual(skill_names, expected_skills)
        self.assertEqual(len(skills), 16)
        self.assertNotIn('HTML & CSS', skill_names)
        self.assertNotIn('Testing', skill_names)
        self.assertNotIn('Testing & Debugging', skill_names)
        self.assertNotIn('JavaScript', skill_names)
        self.assertNotIn('REST API', skill_names)

        # Verify evidence traceability for every skill
        for name in expected_skills:
            self.assertIn(name, evidence)
            self.assertTrue(bool(evidence[name]['sentence']))
            self.assertIn(evidence[name]['section'], ['Technical Skills', 'Projects', 'Education', 'Certifications', 'Summary', 'General'])