#!/usr/bin/env python3
import os
import re
import feedparser
import html2text
import argparse
from datetime import datetime
import unicodedata
import ssl
from urllib.parse import urlparse

def slugify(value):
    """
    Convert string to slug format (lowercase, remove special chars, replace spaces with hyphens)
    """
    # Convert to ASCII
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    # Convert to lowercase
    value = value.lower()
    # Remove non-alphanumeric characters and replace spaces with hyphens
    value = re.sub(r'[^\w\s-]', '', value).strip()
    value = re.sub(r'[-\s]+', '-', value)
    return value

def extract_image_url(content):
    """Extract the first image URL from HTML content if available"""
    img_pattern = re.compile(r'<img[^>]+src="([^">]+)')
    match = img_pattern.search(content)
    if match:
        return match.group(1)
    return ""

def format_date(date_str):
    """Format the date string to YYYY-MM-DD format"""
    try:
        # Parse the date from the RSS feed
        date_obj = datetime(*date_str[:6])
        return date_obj.strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        # If date parsing fails, use current date
        return datetime.now().strftime("%Y-%m-%d")

def extract_categories_and_tags(entry):
    """Extract categories and tags from the RSS entry"""
    categories = []
    tags = []
    
    # Handle different RSS formats for categories and tags
    if hasattr(entry, 'categories'):
        for cat in entry.categories:
            if isinstance(cat, str):
                categories.append(cat)
            elif isinstance(cat, tuple) and len(cat) > 0:
                categories.append(cat[0])
    
    # Some RSS feeds use 'tags' instead of 'categories'
    if hasattr(entry, 'tags'):
        for tag in entry.tags:
            if hasattr(tag, 'term'):
                tags.append(tag.term)
            elif isinstance(tag, str):
                tags.append(tag)
            elif isinstance(tag, tuple) and len(tag) > 0:
                tags.append(tag[0])
    
    # If no specific tags, use some categories as tags
    if not tags and categories:
        tags = categories[:3]  # Use first few categories as tags
    
    # Ensure we have at least one category
    if not categories:
        categories = ["Uncategorized"]
    
    return categories, tags

def create_hugo_article(entry, output_dir):
    """Create a Hugo article from an RSS entry"""
    # Extract the needed information
    title = entry.title
    pub_date = format_date(entry.published_parsed if hasattr(entry, 'published_parsed') else 
                          entry.updated_parsed if hasattr(entry, 'updated_parsed') else None)
    
    # Get author
    author = "Unknown"
    if hasattr(entry, 'author'):
        author = entry.author
    elif hasattr(entry, 'author_detail') and hasattr(entry.author_detail, 'name'):
        author = entry.author_detail.name
    
    # Get categories and tags
    categories, tags = extract_categories_and_tags(entry)
    
    # Get content
    content = ""
    if hasattr(entry, 'content') and entry.content:
        content = entry.content[0].value
    elif hasattr(entry, 'summary'):
        content = entry.summary
    elif hasattr(entry, 'description'):
        content = entry.description
    
    # Convert HTML to Markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0  # No wrapping
    markdown_content = h.handle(content)
    
    # Get image if available
    featured_image = extract_image_url(content)
    
    # Get description
    description = entry.summary if hasattr(entry, 'summary') else ""
    # Strip HTML from description
    description = re.sub(r'<[^>]+>', '', description)
    # Truncate description
    description = description[:160] + "..." if len(description) > 160 else description
    
    # Create filename based on title
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
description: "{description.replace('"', '\\"')}"
---

"""
    
    # Write the file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(front_matter)
        f.write(markdown_content)
    
    return filepath

def process_feed(feed_url, output_dir, max_articles=None):
    """Process an RSS feed and convert entries to Hugo articles"""
    # Fix SSL certificate issues
    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context
    
    # Parse the feed
    feed = feedparser.parse(feed_url)
    
    # Get feed title for subdirectory (optional)
    feed_title = slugify(feed.feed.title) if hasattr(feed.feed, 'title') else "feed"
    feed_dir = os.path.join(output_dir, feed_title)
    
    # Create the output directory if it doesn't exist
    os.makedirs(feed_dir, exist_ok=True)
    
    # Process each entry
    processed_articles = []
    entries = feed.entries[:max_articles] if max_articles else feed.entries
    
    for entry in entries:
        try:
            filepath = create_hugo_article(entry, feed_dir)
            processed_articles.append(filepath)
            print(f"Created article: {filepath}")
        except Exception as e:
            print(f"Error processing entry '{entry.title if hasattr(entry, 'title') else 'Unknown'}': {str(e)}")
    
    return processed_articles

def main():
    parser = argparse.ArgumentParser(description='Convert RSS feeds to Hugo articles')
    parser.add_argument('feed_urls', nargs='+', help='URLs of RSS feeds to process')
    parser.add_argument('--output', '-o', default='articles', help='Output directory for Hugo articles')
    parser.add_argument('--max', '-m', type=int, help='Maximum number of articles to process per feed')
    
    args = parser.parse_args()
    
    # Create the base output directory
    os.makedirs(args.output, exist_ok=True)
    
    total_articles = 0
    
    # Process each feed
    for feed_url in args.feed_urls:
        print(f"\nProcessing feed: {feed_url}")
        articles = process_feed(feed_url, args.output, args.max)
        total_articles += len(articles)
    
    print(f"\nDone! Created {total_articles} Hugo articles in '{args.output}' directory.")

if __name__ == "__main__":
    main()
