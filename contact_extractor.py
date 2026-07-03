"""
Contact Extractor Module - Extract emails, phones, and social profiles from websites
"""
import re
from urllib.parse import urlparse, urljoin
import requests


class ContactExtractor:
    """Extracts contact information from websites"""
    
    # Email pattern
    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )
    
    # US Phone patterns
    PHONE_PATTERNS = [
        re.compile(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),  # (555) 555-5555 or 555-555-5555
        re.compile(r'\+?1[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),  # +1 (555) 555-5555
        re.compile(r'\d{3}[-.\s]\d{3}[-.\s]\d{4}'),  # 555-555-5555
    ]
    
    # Obfuscated email patterns
    OBFUSCATED_PATTERNS = [
        re.compile(r'(\w+)\s*(?:\[at\]|\(at\)|\{at\}| at )\s*(\w+)\s*(?:\[dot\]|\(dot\)|\{dot\}| dot )\s*(\w+)', re.IGNORECASE),
        re.compile(r'(\w+)\s*@\s*(\w+)\s*\.\s*(\w+)', re.IGNORECASE),
    ]
    
    SOCIAL_PATTERNS = {
        'facebook': re.compile(r'facebook\.com/([a-zA-Z][a-zA-Z0-9._-]{4,})', re.IGNORECASE),
        'instagram': re.compile(r'instagram\.com/([a-zA-Z][a-zA-Z0-9._-]{4,})', re.IGNORECASE),
        'linkedin': re.compile(r'linkedin\.com/(?:company|in)/([a-zA-Z][a-zA-Z0-9._-]{4,})', re.IGNORECASE),
        'twitter': re.compile(r'(?:twitter\.com|x\.com)/([a-zA-Z][a-zA-Z0-9._-]{4,})', re.IGNORECASE),
        'youtube': re.compile(r'youtube\.com/(?:c/|channel/|@)([a-zA-Z][a-zA-Z0-9._-]{4,})', re.IGNORECASE),
        'yelp': re.compile(r'yelp\.com/biz/([a-zA-Z][a-zA-Z0-9._-]{4,})', re.IGNORECASE),
    }
    
    WHATSAPP_PATTERN = re.compile(r'wa\.me/(\d+)', re.IGNORECASE)
    TEL_PATTERN = re.compile(r'tel:([+\d()-]+)', re.IGNORECASE)
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; ContactExtractor/1.0)'
        })
    
    def extract_from_html(self, html, url):
        """Extract all contact information from HTML"""
        contacts = {
            'emails': [],
            'phones': [],
            'social_profiles': {},
            'whatsapp': None,
            'contact_page_url': None
        }
        
        # Extract emails
        contacts['emails'] = self._extract_emails(html)
        
        # Extract phones
        contacts['phones'] = self._extract_phones(html)
        
        # Extract social profiles
        contacts['social_profiles'] = self._extract_social_profiles(html)
        
        # Extract WhatsApp
        contacts['whatsapp'] = self._extract_whatsapp(html)
        
        # Find contact page URL
        contacts['contact_page_url'] = self._find_contact_page(html, url)
        
        # Deduplicate
        contacts['emails'] = list(set(contacts['emails']))
        contacts['phones'] = list(set(contacts['phones']))
        
        return contacts
    
    def extract_from_url(self, url):
        """Fetch URL and extract contacts"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return self.extract_from_html(response.text, url)
        except Exception as e:
            return {'error': str(e), 'emails': [], 'phones': [], 'social_profiles': {}}
    
    def extract_from_pages(self, base_url, pages=['/contact', '/about', '/contact-us', '/about-us']):
        """Check multiple pages for contact info"""
        all_contacts = {
            'emails': [],
            'phones': [],
            'social_profiles': {},
            'whatsapp': None
        }
        
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        
        for page in pages:
            try:
                url = urljoin(base, page)
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    contacts = self.extract_from_html(response.text, url)
                    all_contacts['emails'].extend(contacts.get('emails', []))
                    all_contacts['phones'].extend(contacts.get('phones', []))
                    all_contacts['social_profiles'].update(contacts.get('social_profiles', {}))
                    if contacts.get('whatsapp') and not all_contacts['whatsapp']:
                        all_contacts['whatsapp'] = contacts['whatsapp']
            except:
                continue
        
        # Deduplicate
        all_contacts['emails'] = list(set(all_contacts['emails']))
        all_contacts['phones'] = list(set(all_contacts['phones']))
        
        return all_contacts
    
    def _extract_emails(self, html):
        """Extract email addresses"""
        emails = []
        
        # Standard email pattern
        found = self.EMAIL_PATTERN.findall(html)
        emails.extend(found)
        
        # Obfuscated patterns
        for pattern in self.OBFUSCATED_PATTERNS:
            matches = pattern.findall(html)
            for match in matches:
                if len(match) == 3:
                    email = f"{match[0]}@{match[1]}.{match[2]}"
                    emails.append(email)
        
        # Filter out common false positives
        filtered = []
        for email in emails:
            email = email.lower()
            # Skip image extensions, common non-emails
            if not any(ext in email for ext in ['.png', '.jpg', '.gif', '.svg', '.css', '.js']):
                # Skip common false positives
                if not email.startswith(('image', 'icon', 'logo', 'sprite', 'background')):
                    # Skip MHTML bookmarks and browser artifacts
                    if not any(domain in email for domain in ['mhtml.blink', 'mhtml.', '@mhtml']):
                        # Skip common non-business domains
                        if not any(domain in email for domain in ['example.com', 'test.com', 'localhost']):
                            # Validate email structure (must have valid TLD)
                            parts = email.split('@')
                            if len(parts) == 2:
                                domain = parts[1]
                                tld = domain.split('.')[-1]
                                # Skip if TLD is too long or looks like a hash
                                if len(tld) <= 10 and not any(c.isdigit() for c in tld):
                                    filtered.append(email)
        
        return filtered
    
    def _extract_phones(self, html):
        """Extract phone numbers"""
        phones = []
        
        # Extract from tel: links first (most reliable)
        tel_matches = self.TEL_PATTERN.findall(html)
        phones.extend(tel_matches)
        
        # Extract from text
        for pattern in self.PHONE_PATTERNS:
            found = pattern.findall(html)
            phones.extend(found)
        
        # Clean and validate
        cleaned = []
        for phone in phones:
            # Remove non-digits
            digits = re.sub(r'\D', '', phone)
            # US numbers should be 10 or 11 digits
            if len(digits) in [10, 11]:
                cleaned.append(phone.strip())
        
        return cleaned
    
    def _extract_social_profiles(self, html):
        """Extract social media profiles"""
        profiles = {}
        
        for platform, pattern in self.SOCIAL_PATTERNS.items():
            matches = pattern.findall(html)
            if matches:
                profiles[platform] = list(set(matches))[:3]  # Max 3 per platform
        
        return profiles
    
    def _extract_whatsapp(self, html):
        """Extract WhatsApp contact"""
        match = self.WHATSAPP_PATTERN.search(html)
        if match:
            return f"https://wa.me/{match.group(1)}"
        return None
    
    def _find_contact_page(self, html, base_url):
        """Find contact page URL"""
        contact_patterns = [
            r'href=["\']([^"\']*contact[^"\']*)["\']',
            r'href=["\']([^"\']*get-in-touch[^"\']*)["\']',
            r'href=["\']([^"\']*reach-us[^"\']*)["\']',
        ]
        
        for pattern in contact_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                href = match.group(1)
                if href.startswith(('http://', 'https://')):
                    return href
                elif href.startswith('/'):
                    parsed = urlparse(base_url)
                    return f"{parsed.scheme}://{parsed.netloc}{href}"
        
        return None
    
    def format_contacts(self, contacts):
        """Format contacts for display"""
        formatted = []
        
        if contacts.get('emails'):
            formatted.append(f"Email: {', '.join(contacts['emails'])}")
        
        if contacts.get('phones'):
            formatted.append(f"Phone: {', '.join(contacts['phones'])}")
        
        if contacts.get('whatsapp'):
            formatted.append(f"WhatsApp: {contacts['whatsapp']}")
        
        if contacts.get('social_profiles'):
            for platform, handles in contacts['social_profiles'].items():
                formatted.append(f"{platform.title()}: {', '.join(handles)}")
        
        return formatted
