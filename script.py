#!/usr/bin/env python3
import os
import re
import feedparser
import html2text
import argparse
from datetime import datetime
import unicodedata
import ssl

def slugify(value):
    """
    Convert string to slug format (lowercase, remove special chars, replace spaces with hyphens)
    """
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = value.lower()
    value = re.sub(r'[^\w\s-]', '', value).strip()
    value = re.sub(r'[-\s]+', '-', value)
    return value

def extract_image_url(entry, content):
    """Extract image URL from RSS entry using multiple methods"""
    # Method 1: Check for media:content or media:thumbnail
    for key in ['media_content', 'media_thumbnail']:
        if hasattr(entry, key) and entry[key]:
            for media in entry[key]:
                if 'url' in media:
                    return media['url']
    
    # Method 2: Check for enclosures
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enclosure in entry.enclosures:
            if 'type' in enclosure and enclosure.type.startswith('image/') and 'href' in enclosure:
                return enclosure.href
    
    # Method 3: Check for image link in entry links
    if hasattr(entry, 'links'):
        for link in entry.links:
            if 'type' in link and link.type.startswith('image/') and 'href' in link:
                return link.href
    
    # Method 4: Look for <img> tags in content
    img_pattern = re.compile(r'<img[^>]+src="([^">]+)')
    match = img_pattern.search(content)
    if match:
        return match.group(1)
    
    # Method 5: Check for image in entry
    if hasattr(entry, 'image') and entry.image and hasattr(entry.image, 'href'):
        return entry.image.href
    
    # Method 6: Check og:image in content
    og_image_pattern = re.compile(r'<meta[^>]+property="og:image"[^>]+content="([^">]+)')
    match = og_image_pattern.search(content)
    if match:
        return match.group(1)
    
    # No image found
    return ""

def format_date(date_str):
    """Format the date string to YYYY-MM-DD format"""
    try:
        date_obj = datetime(*date_str[:6])
        return date_obj.strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return datetime.now().strftime("%Y-%m-%d")

def extract_categories_and_tags(entry):
    """Extract categories and tags from the RSS entry"""
    categories = [cat if isinstance(cat, str) else cat[0] for cat in getattr(entry, 'categories', [])]
    tags = [tag.term if hasattr(tag, 'term') else tag for tag in getattr(entry, 'tags', [])]
    if not tags and categories:
        tags = categories[:3]
    return categories or ["Uncategorized"], tags

def create_hugo_article(entry, output_dir):
    """Create a Hugo article from an RSS entry"""
    title = entry.title
    pub_date = format_date(getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None))
    author = getattr(entry, 'author', "Unknown")
    categories, tags = extract_categories_and_tags(entry)

    content = (getattr(entry, 'content', [{}])[0].get('value') or
               getattr(entry, 'summary', '') or
               getattr(entry, 'description', ''))

    # Convert HTML to Markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0
    markdown_content = h.handle(content)

    # Extract featured image with improved function
    featured_image = extract_image_url(entry, content)
    description = re.sub(r'<[^>]+>', '', getattr(entry, 'summary', ''))[:160] + "..."

    # Handle special characters in the description
    description = description.replace('\\', '\\\\')  # Escape backslashes
    description = description.replace('"', '\\"')    # Escape double quotes
    description = description.replace('\n', ' ')     # Replace newlines with spaces

    # Save directly inside 'content/articles/'
    filename = slugify(title) + ".md"
    filepath = os.path.join(output_dir, filename)

    # Create front matter
    front_matter = f"""---
title: "{title}"
date: {pub_date}
author: "{author}"
categories: {str(categories).replace("'", '"')}
tags: {str(tags).replace("'", '"')}
featured_image: "{featured_image}"
description: "{description}"
---

"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(front_matter)
        f.write(markdown_content)

    return filepath, featured_image  # Return filepath and image URL for debugging

def process_feed(feed_url, output_dir, max_articles=None, debug=False):
    """Process an RSS feed and convert entries to Hugo articles"""
    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context

    feed = feedparser.parse(feed_url)
    os.makedirs(output_dir, exist_ok=True)  # Ensure output directory exists

    processed_articles = []
    entries = feed.entries[:max_articles] if max_articles else feed.entries

    if debug:
        # Print feed keys for debugging
        print(f"Feed keys: {list(feed.keys())}")
        if 'feed' in feed:
            print(f"Feed info keys: {list(feed.feed.keys())}")
        if entries:
            print(f"Sample entry keys: {list(entries[0].keys())}")

    for entry in entries:
        try:
            filepath, image_url = create_hugo_article(entry, output_dir)
            processed_articles.append(filepath)
            print(f"Created article: {filepath}")
            print(f"  Image URL: {image_url or 'None found'}")
        except Exception as e:
            print(f"Error processing entry '{getattr(entry, 'title', 'Unknown')}': {str(e)}")

    return processed_articles

def main():
    parser = argparse.ArgumentParser(description='Convert RSS feeds to Hugo articles')
    parser.add_argument('feed_urls', nargs='+', help='URLs of RSS feeds to process')
    parser.add_argument('--output', '-o', default='content/articles', help='Output directory for Hugo articles')
    parser.add_argument('--max', '-m', type=int, help='Maximum number of articles to process per feed')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug output')

    args = parser.parse_args()
    os.makedirs(args.output, exist_ok=True)

    total_articles = 0
    for feed_url in args.feed_urls:
        print(f"\nProcessing feed: {feed_url}")
        articles = process_feed(feed_url, args.output, args.max, args.debug)
        total_articles += len(articles)

    print(f"\nDone! Created {total_articles} Hugo articles in '{args.output}' directory.")

if __name__ == "__main__":
    main()
