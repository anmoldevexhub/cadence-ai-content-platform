import re
import logging
import base64
import os
from collections import Counter
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)

STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'if', 'because', 'as', 'until', 'while',
    'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through',
    'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in',
    'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here',
    'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few',
    'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
    'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don',
    'should', 'now', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
    'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
    'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their',
    'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 'these',
    'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
    'had', 'having', 'do', 'does', 'did', 'doing', 'would', 'could', 'should',
    'ought', 'i\'m', 'you\'re', 'he\'s', 'she\'s', 'it\'s', 'we\'re', 'they\'re',
    'i\'ve', 'you\'ve', 'we\'ve', 'they\'ve', 'i\'d', 'you\'d', 'he\'d', 'she\'d',
    'we\'d', 'they\'d', 'i\'ll', 'you\'ll', 'he\'ll', 'she\'ll', 'we\'ll', 'they\'ll',
    'isn\'t', 'aren\'t', 'wasn\'t', 'weren\'t', 'hasn\'t', 'haven\'t', 'hadn\'t',
    'doesn\'t', 'don\'t', 'didn\'t', 'won\'t', 'wouldn\'t', 'shan\'t', 'shouldn\'t',
    'can\'t', 'cannot', 'couldn\'t', 'mustn\'t', 'let\'s', 'that\'s', 'who\'s',
    'what\'s', 'here\'s', 'there\'s', 'when\'s', 'where\'s', 'why\'s', 'how\'s',
    'a\'s', 'c\'s', 't\'s', 'us'
}

CTA_KEYWORDS = {
    'buy', 'order', 'sign up', 'join', 'get', 'subscribe', 'download', 'contact',
    'start', 'register', 'try', 'learn more', 'explore', 'read more', 'click here',
    'shop', 'purchase', 'book', 'schedule', 'view'
}

POSITIVE_WORDS = {
    'good', 'great', 'excellent', 'amazing', 'wonderful', 'love', 'like', 'best', 'awesome', 'happy',
    'positive', 'beautiful', 'fantastic', 'innovative', 'perfect', 'successful', 'improve', 'quality',
    'expert', 'reliable', 'friendly', 'warm', 'satisfying', 'joy', 'benefit', 'easy', 'helpful', 'fast'
}

NEGATIVE_WORDS = {
    'bad', 'poor', 'terrible', 'worst', 'hate', 'dislike', 'awful', 'sad', 'negative', 'ugly',
    'failed', 'failure', 'broken', 'slow', 'difficult', 'expensive', 'useless', 'wrong', 'bug', 'error',
    'issue', 'problem', 'pain', 'frustrating', 'annoyed', 'disappointed', 'complaint', 'delay'
}


def count_syllables(word: str) -> int:
    """Estimates the syllable count of an English word."""
    word = word.lower().strip(".:;!?,-()\"'")
    if not word:
        return 0
    vowels = "aeiouy"
    count = 0
    if word[0] in vowels:
        count += 1
    for index in range(1, len(word)):
        if word[index] in vowels and word[index - 1] not in vowels:
            count += 1
    if word.endswith("e"):
        count -= 1
    if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
        count += 1
    if count <= 0:
        count = 1
    return count


def calculate_readability_metrics(text: str) -> dict:
    """Calculates Flesch Reading Ease, Flesch-Kincaid Grade Level, and Gunning Fog Index."""
    words = re.findall(r'[a-z\']+', text.lower())
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    num_words = len(words)
    num_sentences = len(sentences)
    if num_words == 0 or num_sentences == 0:
        return {
            'flesch_reading_ease': 0.0,
            'flesch_kincaid_grade': 0.0,
            'gunning_fog': 0.0
        }
        
    num_syllables = sum(count_syllables(w) for w in words)
    
    # Flesch Reading Ease
    fre = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words)
    
    # Flesch-Kincaid Grade Level
    fkg = 0.39 * (num_words / num_sentences) + 11.8 * (num_syllables / num_words) - 15.59
    
    # Gunning Fog Index
    complex_words = sum(1 for w in words if count_syllables(w) >= 3)
    gf = 0.4 * ((num_words / num_sentences) + 100.0 * (complex_words / num_words))
    
    return {
        'flesch_reading_ease': round(fre, 1),
        'flesch_kincaid_grade': round(max(fkg, 0.0), 1),
        'gunning_fog': round(max(gf, 0.0), 1)
    }


def analyze_sentiment(text: str) -> dict:
    """Calculates sentiment polarity using TextBlob if enabled/installed, else lexicon fallback."""
    from django.conf import settings
    enable_nlp = getattr(settings, 'ENABLE_ADVANCED_ANALYSIS', False)
    
    if enable_nlp:
        try:
            from textblob import TextBlob
            blob = TextBlob(text)
            return {
                'polarity': round(blob.sentiment.polarity, 2),
                'subjectivity': round(blob.sentiment.subjectivity, 2)
            }
        except ImportError:
            logger.info("TextBlob is not installed, falling back to pure Python sentiment analyzer.")
            
    # Lexicon-based sentiment fallback
    words = re.findall(r'[a-z\']+', text.lower())
    if not words:
        return {'polarity': 0.0, 'subjectivity': 0.0}
        
    pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
    neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
    
    total = pos_count + neg_count
    polarity = (pos_count - neg_count) / total if total > 0 else 0.0
    subjectivity = total / len(words) if len(words) > 0 else 0.0
    subjectivity = min(subjectivity * 10, 1.0)
    
    return {
        'polarity': round(polarity, 2),
        'subjectivity': round(subjectivity, 2)
    }


def extract_entities(text: str) -> list:
    """Extracts common entities (names, organizations) using spaCy if enabled/installed, else pure Python."""
    from django.conf import settings
    enable_nlp = getattr(settings, 'ENABLE_ADVANCED_ANALYSIS', False)
    
    if enable_nlp:
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text[:10000])
            ents = [ent.text.strip() for ent in doc.ents if ent.label_ in {'PERSON', 'ORG', 'GPE'}]
            return [name for name, count in Counter(ents).most_common(10)]
        except Exception:
            logger.info("spaCy failed or is not configured, falling back to pure Python entity extractor.")
            
    # Pure Python named entity heuristics: Capitalized words
    sentences = re.split(r'[.!?]+', text)
    candidates = []
    for sentence in sentences:
        words = sentence.strip().split()
        for i, w in enumerate(words):
            w_clean = re.sub(r'[^\w]', '', w)
            if not w_clean or len(w_clean) <= 2 or not w_clean[0].isupper():
                continue
            if i == 0:
                if w_clean.lower() in STOPWORDS:
                    continue
            candidates.append(w_clean)
                
    return [name for name, count in Counter(candidates).most_common(10)]


def extract_key_phrases(text: str) -> list:
    """Extracts most common collocations/phrases (1-3 words) excluding stopwords."""
    sentences = re.split(r'[.!?,\n;:]+', text.lower())
    phrases = []
    
    for s in sentences:
        words = s.strip().split()
        if not words:
            continue
        curr_phrase = []
        for w in words:
            w_clean = re.sub(r'[^a-z0-9\']', '', w)
            if w_clean in STOPWORDS or len(w_clean) <= 2:
                if curr_phrase:
                    phrases.append(" ".join(curr_phrase))
                    curr_phrase = []
            else:
                curr_phrase.append(w_clean)
        if curr_phrase:
            phrases.append(" ".join(curr_phrase))
            
    # Keep only phrases with 1 to 3 words
    valid_phrases = [p for p in phrases if 0 < len(p.split()) <= 3]
    return [phrase for phrase, count in Counter(valid_phrases).most_common(10)]


def analyze_style_from_pages(pages: list) -> dict:
    """Analyzes scraped pages using heuristics to construct a structured style guide (original structure)."""
    all_text = ""
    all_headings = []
    cta_phrases = set()
    total_sentences = 0
    total_words = 0
    
    first_person_count = 0
    second_person_count = 0
    
    for p in pages:
        text = p.get('text', '')
        all_text += " " + text
        for h in p.get('headings', []):
            all_headings.append(h)
            
        sentences = re.split(r'[.!?]+', text)
        for s in sentences:
            s_clean = s.strip().lower()
            if not s_clean:
                continue
            total_sentences += 1
            words = s_clean.split()
            total_words += len(words)
            for w in words:
                w_clean = re.sub(r'[^a-z\']', '', w)
                if w_clean in {'i', 'we', 'us', 'our', 'my', 'me'}:
                    first_person_count += 1
                elif w_clean in {'you', 'your', 'yours'}:
                    second_person_count += 1
                    
            for keyword in CTA_KEYWORDS:
                if s_clean.startswith(keyword) or f" {keyword} " in f" {s_clean} ":
                    if len(words) <= 10:
                        phrase = re.sub(r'[^\w\s-]', '', s.strip())
                        if phrase:
                            cta_phrases.add(phrase)

    avg_sentence_len = (total_words / total_sentences) if total_sentences > 0 else 15
    fp_ratio = (first_person_count / total_words) if total_words > 0 else 0
    sp_ratio = (second_person_count / total_words) if total_words > 0 else 0
    
    if fp_ratio > 0.02 and sp_ratio > 0.02:
        tone_label = "Highly conversational, relational, and customer-focused"
    elif fp_ratio > 0.015:
        tone_label = "First-person storytelling, informal, and casual"
    elif sp_ratio > 0.02:
        tone_label = "Direct-address, instructional, and action-oriented"
    elif avg_sentence_len > 18:
        tone_label = "Formal, analytical, and professional"
    else:
        tone_label = "Neutral, informative, and engaging"

    words_only = re.findall(r'[a-z\']+', all_text.lower())
    filtered_words = [w for w in words_only if w not in STOPWORDS and len(w) > 2]
    common_vocab = [word for word, count in Counter(filtered_words).most_common(12)]

    h_levels = Counter([h['level'] for h in all_headings])
    h_question_count = sum(1 for h in all_headings if any(h['text'].lower().startswith(q) for q in ['how', 'why', 'what', 'is', 'are', 'should']))
    
    heading_style = "Balanced mix of H2 and H3 subsections."
    if h_levels.get('h2', 0) > h_levels.get('h3', 0) * 2:
        heading_style = "Heavy use of H2 section dividers, with few H3 subtopics."
    elif h_levels.get('h3', 0) > h_levels.get('h2', 0) * 1.5:
        heading_style = "Extensive H3 subheadings for granular detail under H2 dividers."
        
    if h_question_count > len(all_headings) * 0.25:
        heading_style += " Frequently framed as questions (e.g. 'How to...', 'Why...')."

    ctas_list = sorted(list(cta_phrases))[:6]
    if not ctas_list:
        ctas_list = ["Learn More", "Get Started", "Contact Us"]

    return {
        "primary_tone": tone_label,
        "average_sentence_length": f"{avg_sentence_len:.1f} words",
        "heading_pattern": heading_style,
        "recurring_vocabulary": common_vocab,
        "call_to_action_examples": ctas_list
    }


def build_advanced_style_guide(website_id: int, homepage_styles: dict = None) -> dict:
    """Synthesizes all scraped page results for a website into a single style guide dictionary."""
    from .models import Website, ScrapeResult
    website = Website.objects.get(pk=website_id)
    pages = ScrapeResult.objects.filter(website=website)
    
    if not pages.exists():
        return {}
        
    all_categories = []
    all_authors = []
    fre_scores = []
    fkg_scores = []
    gf_scores = []
    sentiment_polarities = []
    all_ctas = []
    word_counts = []
    all_key_phrases = []
    all_headings = []
    
    for page in pages:
        if page.categories_tags:
            all_categories.extend(page.categories_tags)
        if page.author:
            all_authors.append(page.author)
            
        readability = page.readability_metrics or {}
        if 'flesch_reading_ease' in readability:
            fre_scores.append(readability['flesch_reading_ease'])
        if 'flesch_kincaid_grade' in readability:
            fkg_scores.append(readability['flesch_kincaid_grade'])
        if 'gunning_fog' in readability:
            gf_scores.append(readability['gunning_fog'])
            
        sentiment = page.sentiment_metrics or {}
        if 'polarity' in sentiment:
            sentiment_polarities.append(sentiment['polarity'])
            
        if page.ctas:
            all_ctas.extend(page.ctas)
            
        word_counts.append(page.raw_text.split() if page.raw_text else [])
        
        if page.key_phrases:
            all_key_phrases.extend(page.key_phrases)
            
        if page.heading_structure:
            all_headings.extend(page.heading_structure)
            
    # Aggregations
    cat_counts = Counter(all_categories)
    dominant_categories = [cat for cat, count in cat_counts.most_common(5)]
    
    author_counts = Counter(all_authors)
    common_authors = [{'name': name, 'count': count} for name, count in author_counts.most_common(5)]
    
    avg_fre = sum(fre_scores) / len(fre_scores) if fre_scores else 60.0
    avg_fkg = sum(fkg_scores) / len(fkg_scores) if fkg_scores else 8.0
    avg_gf = sum(gf_scores) / len(gf_scores) if gf_scores else 10.0
    
    avg_polarity = sum(sentiment_polarities) / len(sentiment_polarities) if sentiment_polarities else 0.0
    
    cta_counts = Counter(all_ctas)
    frequent_ctas = [cta for cta, count in cta_counts.most_common(5)]
    if not frequent_ctas:
        frequent_ctas = ["Learn More", "Get Started", "Contact Us"]
        
    avg_word_count = int(sum(len(w) for w in word_counts) / len(word_counts)) if word_counts else 0
    
    phrase_counts = Counter(all_key_phrases)
    common_vocab = [phrase for phrase, count in phrase_counts.most_common(15)]
    
    # Headings Analysis
    h_levels = Counter([h.get('level', '') for h in all_headings])
    h_question_count = sum(1 for h in all_headings if any(str(h.get('text', '')).lower().startswith(q) for q in ['how', 'why', 'what', 'is', 'are', 'should']))
    
    heading_style = "Balanced mix of H2 and H3 subsections."
    if h_levels.get('h2', 0) > h_levels.get('h3', 0) * 2:
        heading_style = "Heavy use of H2 section dividers, with few H3 subtopics."
    elif h_levels.get('h3', 0) > h_levels.get('h2', 0) * 1.5:
        heading_style = "Extensive H3 subheadings for granular detail under H2 dividers."
        
    if h_question_count > len(all_headings) * 0.25:
        heading_style += " Frequently framed as questions (e.g. 'How to...', 'Why...')."
        
    # Tone Calculations
    total_sentences = 0
    total_words = 0
    first_person_count = 0
    second_person_count = 0
    
    for page in pages:
        text = page.raw_text
        sentences = re.split(r'[.!?]+', text)
        for s in sentences:
            s_clean = s.strip().lower()
            if not s_clean:
                continue
            total_sentences += 1
            words = s_clean.split()
            total_words += len(words)
            for w in words:
                w_clean = re.sub(r'[^a-z\']', '', w)
                if w_clean in {'i', 'we', 'us', 'our', 'my', 'me'}:
                    first_person_count += 1
                elif w_clean in {'you', 'your', 'yours'}:
                    second_person_count += 1
                    
    avg_sentence_len = (total_words / total_sentences) if total_sentences > 0 else 15
    fp_ratio = (first_person_count / total_words) if total_words > 0 else 0
    sp_ratio = (second_person_count / total_words) if total_words > 0 else 0
    
    if fp_ratio > 0.02 and sp_ratio > 0.02:
        tone_label = "Highly conversational, relational, and customer-focused"
    elif fp_ratio > 0.015:
        tone_label = "First-person storytelling, informal, and casual"
    elif sp_ratio > 0.02:
        tone_label = "Direct-address, instructional, and action-oriented"
    elif avg_sentence_len > 18:
        tone_label = "Formal, analytical, and professional"
    else:
        tone_label = "Neutral, informative, and engaging"
        
    style_guide_data = {
        "primary_tone": tone_label,
        "average_sentence_length": f"{avg_sentence_len:.1f} words",
        "heading_pattern": heading_style,
        "recurring_vocabulary": common_vocab,
        "call_to_action_examples": frequent_ctas,
        "dominant_topics": dominant_categories,
        "common_authors": common_authors,
        "average_readability_score": round(avg_fre, 1),
        "average_grade_level": round(max(avg_fkg, 0.0), 1),
        "average_gunning_fog": round(max(avg_gf, 0.0), 1),
        "average_sentiment_polarity": round(avg_polarity, 2),
        "typical_post_length_words": avg_word_count,
        "primary_font": homepage_styles.get("primary_font", "") if homepage_styles else "",
        "heading_font": homepage_styles.get("heading_font", "") if homepage_styles else "",
        "heading_color": homepage_styles.get("heading_color", "") if homepage_styles else "",
        "text_color": homepage_styles.get("text_color", "") if homepage_styles else "",
    }
    
    website.style_guide = style_guide_data
    website.save(update_fields=['style_guide'])
    return style_guide_data


def save_logo_from_base64(website, base64_data) -> str:
    try:
        from django.conf import settings
        if ',' in base64_data:
            header, encoded = base64_data.split(",", 1)
        else:
            header, encoded = "", base64_data
            
        ext = "png"
        if "image/svg" in header:
            ext = "svg"
        elif "image/jpeg" in header or "image/jpg" in header:
            ext = "jpg"
        elif "image/gif" in header:
            ext = "gif"
            
        data = base64.b64decode(encoded)
        
        logos_dir = os.path.join(settings.BASE_DIR, 'frontend', 'media', 'logos')
        os.makedirs(logos_dir, exist_ok=True)
        
        filename = f"logo_{website.id}.{ext}"
        filepath = os.path.join(logos_dir, filename)
        
        for other_ext in ['svg', 'png', 'jpg', 'jpeg', 'gif']:
            if other_ext != ext:
                old_path = os.path.join(logos_dir, f"logo_{website.id}.{other_ext}")
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass
                        
        with open(filepath, 'wb') as f:
            f.write(data)
            
        return f"/static/media/logos/{filename}"
    except Exception as e:
        logger.error(f"Failed to save base64 logo: {e}")
        return ""


def download_and_save_logo(website, logo_url) -> str:
    if not logo_url or logo_url.startswith('/static/'):
        return logo_url
    try:
        from django.conf import settings
        resp = requests.get(logo_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if resp.status_code != 200:
            return logo_url
            
        content_type = resp.headers.get('content-type', '').lower()
        ext = 'png'
        if 'svg' in content_type:
            ext = 'svg'
        elif 'jpeg' in content_type or 'jpg' in content_type:
            ext = 'jpg'
        elif 'gif' in content_type:
            ext = 'gif'
        else:
            path = urlparse(logo_url).path
            for possible_ext in ['svg', 'png', 'jpg', 'jpeg', 'gif']:
                if path.endswith(f'.{possible_ext}'):
                    ext = possible_ext
                    break
                    
        logos_dir = os.path.join(settings.BASE_DIR, 'frontend', 'media', 'logos')
        os.makedirs(logos_dir, exist_ok=True)
        filename = f"logo_{website.id}.{ext}"
        filepath = os.path.join(logos_dir, filename)
        
        for other_ext in ['svg', 'png', 'jpg', 'jpeg', 'gif']:
            if other_ext != ext:
                old_path = os.path.join(logos_dir, f"logo_{website.id}.{other_ext}")
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass
                        
        with open(filepath, 'wb') as f:
            f.write(resp.content)
            
        return f"/static/media/logos/{filename}"
    except Exception as e:
        logger.warning(f"Failed to download remote logo: {e}")
        return logo_url
