# src/nlp/job_detector.py

import re
from typing import List, Dict, Optional

class JobDetector:
    """
    Detects job-related messages and extracts structured job info.
    Currently keyword + regex based, extendable with embeddings / ML.
    """

    JOB_KEYWORDS = [
        "hiring", "job", "vacancy", "opening", "position", 
        "career", "opportunity", "internship"
    ]

    # Simple regex patterns for job info
    ROLE_PATTERN = re.compile(r"(?:role|position|job)\s*[:\-]\s*(.+)", re.IGNORECASE)
    COMPANY_PATTERN = re.compile(r"(?:company|org|organization)\s*[:\-]\s*(.+)", re.IGNORECASE)
    LOCATION_PATTERN = re.compile(r"(?:location|based in)\s*[:\-]\s*(.+)", re.IGNORECASE)
    SALARY_PATTERN = re.compile(r"(?:salary|ctc|stipend)\s*[:\-]\s*(.+)", re.IGNORECASE)
    LINK_PATTERN = re.compile(r"(https?://\S+)", re.IGNORECASE)
    EMAIL_PATTERN = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+", re.IGNORECASE)        

    def __init__(self):
        pass

    def is_job_post(self, text: str) -> bool:
        """Check if a message looks like a job post based on keywords."""
        return any(keyword.lower() in text.lower() for keyword in self.JOB_KEYWORDS)
    
    def extract_links(self, text: str) -> List[str]:
        """Extract URLs from text."""
        return self.LINK_PATTERN.findall(text)

    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text."""
        return self.EMAIL_PATTERN.findall(text)

    def extract_field(self, pattern: re.Pattern, text: str) -> Optional[str]:
        """Extract a field value using regex pattern."""
        match = pattern.search(text)
        return match.group(1).strip() if match else None

    def parse_job(self, text: str) -> Optional[Dict]:
        """Extract structured job info from text if it looks like a job post."""
        if not self.is_job_post(text):
            return None

        return {
            "role": self.extract_field(self.ROLE_PATTERN, text),
            "company": self.extract_field(self.COMPANY_PATTERN, text),
            "location": self.extract_field(self.LOCATION_PATTERN, text),
            "salary": self.extract_field(self.SALARY_PATTERN, text),
            "links": self.extract_links(text),
            "emails": self.extract_emails(text),
            "raw_text": text.strip()
        }

    def detect_jobs(self, messages: List[str]) -> List[Dict]:
        """Process a list of messages and return detected jobs."""
        jobs = []
        for msg in messages:
            job = self.parse_job(msg)
            if job:
                jobs.append(job)
        return jobs


if __name__ == "__main__":
    # Quick test
    detector = JobDetector()
    sample_msgs = [
        "Hiring: Software Engineer\nCompany: OpenAI\nLocation: Remote\nSalary: $120k",
        "Let’s catch up tomorrow!",
        "New job opening: Data Analyst at Google, Location: Bangalore"
    ]
    jobs = detector.detect_jobs(sample_msgs)
    for j in jobs:
        print(j)
