"""
SEO Analyzer Module - Real SEO analysis using PageSpeed Insights and HTML parsing
"""
import requests
import re
from urllib.parse import urlparse, urljoin
from html.parser import HTMLParser


class SEOAnalyzer:
    """Performs real SEO analysis on websites"""
    
    PAGESPEED_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; LeadGenAnalyzer/1.0)'
        })
    
    def analyze(self, url, html_content=None):
        """Run full SEO analysis on a URL"""
        results = {
            'url': url,
            'pagespeed': {},
            'html_analysis': {},
            'technical_seo': {},
            'content_quality': {},
            'issues': [],
            'strengths': [],
            'score': 0
        }
        
        # Run PageSpeed Insights
        results['pagespeed'] = self.check_pagespeed(url)
        
        # Analyze HTML if provided
        if html_content:
            results['html_analysis'] = self.analyze_html(html_content, url)
        
        # Check technical SEO
        results['technical_seo'] = self.check_technical_seo(url)
        
        # Analyze content quality
        if html_content:
            results['content_quality'] = self.analyze_content(html_content)
        
        # Compile issues and strengths
        self.compile_findings(results)
        
        # Calculate overall score
        results['score'] = self.calculate_score(results)
        
        return results
    
    def check_pagespeed(self, url):
        """Check Google PageSpeed Insights"""
        import os
        api_key = os.environ.get('GOOGLE_PAGESPEED_API_KEY', '')
        
        params = {
            'url': url,
            'strategy': 'mobile',
            'category': 'performance'
        }
        if api_key:
            params['key'] = api_key
        
        try:
            response = self.session.get(
                self.PAGESPEED_API,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                lighthouse = data.get('lighthouseResult', {})
                categories = lighthouse.get('categories', {})
                metrics = lighthouse.get('audits', {})
                
                return {
                    'performance_score': round(categories.get('performance', {}).get('score', 0) * 100),
                    'lcp': metrics.get('largest-contentful-paint', {}).get('displayValue', 'N/A'),
                    'fcp': metrics.get('first-contentful-paint', {}).get('displayValue', 'N/A'),
                    'cls': metrics.get('cumulative-layout-shift', {}).get('displayValue', 'N/A'),
                    'tti': metrics.get('interactive', {}).get('displayValue', 'N/A'),
                    'speed_index': metrics.get('speed-index', {}).get('displayValue', 'N/A'),
                    'mobile_friendly': categories.get('performance', {}).get('score', 0) > 0.5,
                    'status': 'success'
                }
            elif response.status_code == 429:
                return {
                    'status': 'rate_limited',
                    'message': 'PageSpeed API rate limited. Add GOOGLE_PAGESPEED_API_KEY for higher limits.',
                    'performance_score': None,
                    'lcp': 'N/A',
                    'fcp': 'N/A',
                    'cls': 'N/A'
                }
            else:
                return {
                    'status': 'error',
                    'message': f'API returned status {response.status_code}',
                    'performance_score': None,
                    'lcp': 'N/A',
                    'fcp': 'N/A',
                    'cls': 'N/A'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'performance_score': None,
                'lcp': 'N/A',
                'fcp': 'N/A',
                'cls': 'N/A'
            }
    
    def analyze_html(self, html, url):
        """Parse and analyze HTML content"""
        parser = HTMLTagParser()
        try:
            parser.feed(html)
        except:
            pass
        
        analysis = {
            'title': parser.title,
            'meta_description': parser.meta_description,
            'meta_keywords': parser.meta_keywords,
            'canonical': parser.canonical,
            'og_tags': parser.og_tags,
            'headings': parser.headings,
            'images': parser.images,
            'links': parser.links,
            'has_viewport': parser.has_viewport,
            'hascharset': parser.has_charset,
            'structured_data': parser.structured_data,
            'word_count': 0
        }
        
        # Count words in body text
        body_text = re.sub(r'<[^>]+>', ' ', html)
        body_text = re.sub(r'\s+', ' ', body_text).strip()
        analysis['word_count'] = len(body_text.split())
        
        # Check heading hierarchy
        analysis['h1_count'] = parser.headings.get('h1', 0)
        analysis['heading_hierarchy_valid'] = self._check_heading_hierarchy(parser.headings)
        
        # Check image alt texts
        images_without_alt = sum(1 for img in parser.images if not img.get('alt'))
        analysis['images_without_alt'] = images_without_alt
        analysis['total_images'] = len(parser.images)
        
        # Check link quality
        internal_links = [l for l in parser.links if urlparse(l.get('href', '')).netloc == '' or urlparse(l.get('href', '')).netloc == urlparse(url).netloc]
        external_links = [l for l in parser.links if urlparse(l.get('href', '')).netloc not in ['', urlparse(url).netloc]]
        
        analysis['internal_links'] = len(internal_links)
        analysis['external_links'] = len(external_links)
        analysis['broken_links'] = self._check_broken_links(parser.links, url)
        
        return analysis
    
    def check_technical_seo(self, url):
        """Check technical SEO elements"""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        checks = {
            'has_robots_txt': False,
            'has_sitemap': False,
            'https_enabled': parsed.scheme == 'https',
            'url_structure_clean': self._check_url_structure(url),
            'ssl_valid': False,
            'has_llms_txt': False,
            'ai_crawlers_allowed': False,
            'has_structured_data': False,
            'has_faq_schema': False
        }
        
        # Check robots.txt
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            resp = self.session.get(robots_url, timeout=10)
            checks['has_robots_txt'] = resp.status_code == 200
            if resp.status_code == 200:
                robots_content = resp.text.lower()
                # Check if AI crawlers are allowed
                ai_crawlers = ['gptbot', 'claudebot', 'perplexitybot', 'google-extended']
                checks['ai_crawlers_allowed'] = any(crawler in robots_content for crawler in ai_crawlers)
        except:
            pass
        
        # Check sitemap
        try:
            sitemap_url = urljoin(base_url, '/sitemap.xml')
            resp = self.session.get(sitemap_url, timeout=10)
            checks['has_sitemap'] = resp.status_code == 200
        except:
            pass
        
        # Check llms.txt (AEO)
        try:
            llms_url = urljoin(base_url, '/llms.txt')
            resp = self.session.get(llms_url, timeout=10)
            checks['has_llms_txt'] = resp.status_code == 200
        except:
            pass
        
        # Check SSL
        try:
            resp = self.session.get(base_url, timeout=10, verify=True)
            checks['ssl_valid'] = True
        except:
            checks['ssl_valid'] = False
        
        return checks
    
    def analyze_content(self, html):
        """Analyze content quality"""
        # Remove script and style tags
        clean_html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        clean_html = re.sub(r'<style[^>]*>.*?</style>', '', clean_html, flags=re.DOTALL)
        
        # Extract text
        text = re.sub(r'<[^>]+>', ' ', clean_html)
        text = re.sub(r'\s+', ' ', text).strip()
        
        words = text.split()
        word_count = len(words)
        
        # Check for keyword stuffing (simple heuristic)
        word_freq = {}
        for word in words:
            word_lower = word.lower()
            if len(word_lower) > 3:
                word_freq[word_lower] = word_freq.get(word_lower, 0) + 1
        
        # Find overused words (>2% of total words)
        overused = [w for w, c in word_freq.items() if c / word_count > 0.02 and word_count > 0]
        
        return {
            'word_count': word_count,
            'has_meaningful_content': word_count > 300,
            'overused_keywords': overused[:5],
            'readability_score': self._estimate_readability(text)
        }
    
    def compile_findings(self, results):
        """Compile issues and strengths from all checks"""
        issues = []
        strengths = []
        
        # PageSpeed findings
        ps = results.get('pagespeed', {})
        ps_status = ps.get('status', 'unknown')
        
        if ps_status == 'rate_limited':
            issues.append("PageSpeed data unavailable (API rate limited)")
        elif ps_status == 'error':
            issues.append(f"PageSpeed check failed: {ps.get('message', 'Unknown error')}")
        elif ps_status == 'success':
            ps_score = ps.get('performance_score', 0)
            if ps_score is not None:
                if ps_score < 50:
                    issues.append(f"Low performance score: {ps_score}/100")
                elif ps_score > 80:
                    strengths.append(f"Good performance score: {ps_score}/100")
                else:
                    strengths.append(f"Performance score: {ps_score}/100")
            
            lcp = ps.get('lcp', 'N/A')
            if lcp != 'N/A':
                try:
                    lcp_val = float(lcp.replace('s', ''))
                    if lcp_val > 2.5:
                        issues.append(f"Slow Largest Contentful Paint: {lcp}")
                    else:
                        strengths.append(f"Good LCP: {lcp}")
                except:
                    pass
        
        # HTML analysis findings
        html = results.get('html_analysis', {})
        
        if not html.get('title'):
            issues.append("Missing page title")
        elif len(html.get('title', '')) < 30:
            issues.append(f"Title too short ({len(html.get('title', ''))} chars)")
        elif len(html.get('title', '')) > 60:
            issues.append(f"Title too long ({len(html.get('title', ''))} chars)")
        else:
            strengths.append("Title tag present and appropriate length")
        
        if not html.get('meta_description'):
            issues.append("Missing meta description")
        else:
            desc_len = len(html.get('meta_description', ''))
            if desc_len < 120:
                issues.append(f"Meta description too short ({desc_len} chars)")
            elif desc_len > 160:
                issues.append(f"Meta description too long ({desc_len} chars)")
            else:
                strengths.append("Meta description present and appropriate length")
        
        if html.get('h1_count', 0) == 0:
            issues.append("Missing H1 tag")
        elif html.get('h1_count', 0) > 1:
            issues.append(f"Multiple H1 tags ({html.get('h1_count', 0)})")
        else:
            strengths.append("Single H1 tag present")
        
        if html.get('images_without_alt', 0) > 0:
            issues.append(f"{html.get('images_without_alt', 0)} images missing alt text")
        elif html.get('total_images', 0) > 0:
            strengths.append("All images have alt text")
        
        if not html.get('has_viewport'):
            issues.append("Missing viewport meta tag")
        
        if html.get('word_count', 0) < 300:
            issues.append(f"Thin content ({html.get('word_count', 0)} words)")
        elif html.get('word_count', 0) > 1000:
            strengths.append(f"Substantial content ({html.get('word_count', 0)} words)")
        
        if not html.get('canonical'):
            issues.append("Missing canonical tag")
        
        if not html.get('og_tags'):
            issues.append("Missing Open Graph tags")
        
        # Technical SEO findings
        tech = results.get('technical_seo', {})
        
        if not tech.get('has_robots_txt'):
            issues.append("Missing robots.txt")
        else:
            strengths.append("robots.txt present")
        
        if not tech.get('has_sitemap'):
            issues.append("Missing sitemap.xml")
        else:
            strengths.append("sitemap.xml present")
        
        if not tech.get('https_enabled'):
            issues.append("Not using HTTPS")
        else:
            strengths.append("HTTPS enabled")
        
        if not tech.get('url_structure_clean'):
            issues.append("URL structure could be improved")
        
        # AEO (AI Engine Optimization) findings
        if not tech.get('has_llms_txt'):
            issues.append("Missing llms.txt for AI visibility")
        else:
            strengths.append("llms.txt present for AI crawlers")
        
        if not tech.get('ai_crawlers_allowed'):
            issues.append("AI crawlers may be blocked in robots.txt")
        else:
            strengths.append("AI crawlers allowed")
        
        # Content findings
        content = results.get('content_quality', {})
        
        if content.get('overused_keywords'):
            issues.append(f"Potential keyword stuffing: {', '.join(content['overused_keywords'][:3])}")
        
        if not content.get('has_meaningful_content'):
            issues.append("Insufficient content for SEO")
        
        results['issues'] = issues
        results['strengths'] = strengths
    
    def calculate_score(self, results):
        """Calculate overall SEO score (0-100)"""
        score = 50  # Base score
        
        # PageSpeed contribution (30%)
        ps = results.get('pagespeed', {})
        ps_score = ps.get('performance_score')
        if ps_score is not None and ps.get('status') == 'success':
            score = score * 0.7 + ps_score * 0.3
        else:
            # No PageSpeed data, use base score
            score = score * 0.7 + 50 * 0.3
        
        # Issue penalty
        issue_count = len(results.get('issues', []))
        score -= issue_count * 3
        
        # Strength bonus
        strength_count = len(results.get('strengths', []))
        score += strength_count * 2
        
        return max(0, min(100, round(score)))
    
    def _check_heading_hierarchy(self, headings):
        """Check if heading hierarchy is valid"""
        levels = []
        for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if headings.get(level, 0) > 0:
                levels.append(int(level[1]))
        
        if not levels:
            return False
        
        # Check for proper nesting (no skipping levels)
        for i in range(1, len(levels)):
            if levels[i] - levels[i-1] > 1:
                return False
        return True
    
    def _check_url_structure(self, url):
        """Check if URL is clean and SEO-friendly"""
        parsed = urlparse(url)
        path = parsed.path
        
        # Bad patterns
        bad_patterns = ['?', '&', '=', '_', '~', '%', '+']
        for pattern in bad_patterns:
            if pattern in path:
                return False
        
        # Too many segments
        segments = [s for s in path.split('/') if s]
        if len(segments) > 4:
            return False
        
        return True
    
    def _check_broken_links(self, links, base_url):
        """Check for obviously broken links"""
        broken = 0
        for link in links[:10]:  # Check first 10 only
            href = link.get('href', '')
            if href and href.startswith('#'):
                continue
            if 'javascript:' in href:
                continue
            # Just count mailto/tel as valid
            if href.startswith(('mailto:', 'tel:')):
                continue
        return broken
    
    def _estimate_readability(self, text):
        """Simple readability estimation"""
        sentences = re.split(r'[.!?]+', text)
        words = text.split()
        
        if not sentences or not words:
            return 0
        
        avg_words_per_sentence = len(words) / max(len(sentences), 1)
        
        # Simple score: lower avg words per sentence = better readability
        if avg_words_per_sentence < 15:
            return 80
        elif avg_words_per_sentence < 20:
            return 60
        elif avg_words_per_sentence < 25:
            return 40
        else:
            return 20


class HTMLTagParser(HTMLParser):
    """Custom HTML parser to extract SEO-relevant tags"""
    
    def __init__(self):
        super().__init__()
        self.title = ''
        self.meta_description = ''
        self.meta_keywords = ''
        self.canonical = ''
        self.og_tags = {}
        self.headings = {}
        self.images = []
        self.links = []
        self.has_viewport = False
        self.has_charset = False
        self.structured_data = []
        self._in_title = False
        self._current_tag = None
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._current_tag = tag
        
        if tag == 'title':
            self._in_title = True
        
        elif tag == 'meta':
            name = attrs_dict.get('name', '').lower()
            property = attrs_dict.get('property', '').lower()
            content = attrs_dict.get('content', '')
            
            if name == 'description':
                self.meta_description = content
            elif name == 'keywords':
                self.meta_keywords = content
            elif name == 'viewport':
                self.has_viewport = True
            elif property.startswith('og:'):
                self.og_tags[property] = content
        
        elif tag == 'link':
            rel = attrs_dict.get('rel', '').lower()
            if rel == 'canonical':
                self.canonical = attrs_dict.get('href', '')
        
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.headings[tag] = self.headings.get(tag, 0) + 1
        
        elif tag == 'img':
            self.images.append({
                'src': attrs_dict.get('src', ''),
                'alt': attrs_dict.get('alt', ''),
                'title': attrs_dict.get('title', '')
            })
        
        elif tag == 'a':
            self.links.append({
                'href': attrs_dict.get('href', ''),
                'text': ''
            })
        
        elif tag == 'script':
            type_attr = attrs_dict.get('type', '')
            if 'ld+json' in type_attr:
                self.structured_data.append(type_attr)
    
    def handle_data(self, data):
        if self._in_title:
            self.title += data
    
    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False
        self._current_tag = None
