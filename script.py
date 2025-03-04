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

def extract_image_url(content):
    """Extract the first image URL from HTML content if available"""
    img_pattern = re.compile(r'<img[^>]+src="([^">]+)')
    match = img_pattern.search(content)
    return match.group(1) if match else ""

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

    featured_image = extract_image_url(content)
    description = re.sub(r'<[^>]+>', '', getattr(entry, 'summary', ''))[:160] + "..."

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

    return filepath

def process_feed(feed_url, output_dir, max_articles=None):
    """Process an RSS feed and convert entries to Hugo articles"""
    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context

    feed = feedparser.parse(feed_url)
    os.makedirs(output_dir, exist_ok=True)  # Ensure 'content/articles/' exists

    processed_articles = []
    entries = feed.entries[:max_articles] if max_articles else feed.entries

    for entry in entries:
        try:
            filepath = create_hugo_article(entry, output_dir)
            processed_articles.append(filepath)
            print(f"Created article: {filepath}")
        except Exception as e:
            print(f"Error processing entry '{getattr(entry, 'title', 'Unknown')}': {str(e)}")

    return processed_articles

def main():
    parser = argparse.ArgumentParser(description='Convert RSS feeds to Hugo articles')
    parser.add_argument('feed_urls', nargs='+', help='URLs of RSS feeds to process')
    parser.add_argument('--output', '-o', default='content/articles', help='Output directory for Hugo articles')
    parser.add_argument('--max', '-m', type=int, help='Maximum number of articles to process per feed')

    args = parser.parse_args()
    os.makedirs(args.output, exist_ok=True)

    total_articles = 0
    for feed_url in args.feed_urls:
        print(f"\nProcessing feed: {feed_url}")
        articles = process_feed(feed_url, args.output, args.max)
        total_articles += len(articles)

    print(f"\nDone! Created {total_articles} Hugo articles in '{args.output}' directory.")

if __name__ == "__main__":
    main()
