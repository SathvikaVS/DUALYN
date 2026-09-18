from django.db import models
from django.contrib.auth.models import User

class Student_Profile(models.Model):

    EDUCATION_CHOICES = [('Undergad', 'Undegraduate'),
                         ('Postgrad', 'Postgraduate'),
                         ('PhD', 'PhD / Reasearch')]

    CARRER_INTERST_CHOICES =[('Industry', 'Industry / Job'), 
                             ('Masters', 'Masters / Postgraduate'),
                             ('Research', 'Research / PhD'), 
                             ('Entrepreneurship', 'Entrepreneurship / Startup'),
                             ('Other', 'Other'), ('Undecided', 'Still deciding')]

    STATUS_CHOICES = [('Studying', 'Studying'), ('Working', 'Working'), ('Looking for opportunities', 'Looking for opportunities'),
                      ('Taking a break', 'Taking a break'), ('Other', 'Other')]

    Year_CHOICES = [('1', '1st Year'), ('2', '2nd Year'), ('3', '3rd Year'),
                    ('4', '4th Year'), ('5', '5th Year')]
    

    User = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    Full_name = models.CharField(max_length=100)
    Education = models.CharField(max_length=20, choices=EDUCATION_CHOICES, default='Undergad')
    College = models.CharField(max_length=100)
    Carrer_Interest = models.CharField(max_length=20, choices=CARRER_INTERST_CHOICES, default='Undecided')
    Status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Studying')
    
    Year_of_Study = models.IntegerField(choices=Year_CHOICES, null=True, blank=True)
    Years_of_Experience = models.PositiveIntegerField(null=True, blank=True)

    User_registerd = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.status == 'studying' and self.year_of_study is None:
            raise ValidationError({'year_of_study': 'Please select your year of study.'})

        if self.status == 'working' and self.years_of_experience is None:
            raise ValidationError({'years_of_experience': 'Please enter your years of experience.'})

    def __str__(self):
        return self.full_name

    

