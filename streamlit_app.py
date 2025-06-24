import json
import re
import time
import random
from urllib.parse import urlparse, urljoin

import streamlit as st
import requests
from bs4 import BeautifulSoup


class TourScraper:
    def __init__(self):
        self.session = requests.Session()
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def check_robots_txt(self, base_url):
        """Check robots.txt to understand crawling restrictions"""
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            response = self.session.get(robots_url, timeout=10)
            if response.status_code == 200:
                # Add a small delay to be respectful
                time.sleep(random.uniform(1, 3))
            return True
        except Exception:
            return True
    
    def fetch_page(self, url):
        """Fetch the webpage content"""
        try:
            # Add random delay to avoid being blocked
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch page: {e}")
    
    def clean_text(self, text):
        """Clean text by replacing Unicode characters with ASCII equivalents"""
        if not text:
            return text
        
        # Replace Unicode characters with ASCII equivalents
        replacements = {
            '\u2013': '-',  # en dash → hyphen
            '\u2014': '-',  # em dash → hyphen
            '\u2019': "'",  # right single quotation mark → apostrophe
            '\u2018': "'",  # left single quotation mark → apostrophe
            '\u201c': '"',  # left double quotation mark → straight quote
            '\u201d': '"',  # right double quotation mark → straight quote
            '\u2026': '...',  # horizontal ellipsis → three dots
        }
        
        for unicode_char, ascii_char in replacements.items():
            text = text.replace(unicode_char, ascii_char)
        
        return text

    def parse_itinerary_description(self, soup):
        """Extract the itinerary description/summary"""
        # Look for the itinerary description section
        description_elem = soup.find('div', class_='ao-clp-custom-tdp-itinerary__description')
        if description_elem:
            # Get text and clean up extra whitespace
            text = description_elem.get_text(strip=True)
            text = self.clean_text(text)
            # Split into sentences and clean up
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            return ['. '.join(sentences)]
        return [""]
    
    def parse_itinerary_days(self, soup):
        """Extract individual day itineraries"""
        itinerary_items = []
        
        # Find the itinerary section specifically (not inclusions)
        itinerary_section = soup.find('section', class_='ao-clp-custom-tdp-itinerary')
        if not itinerary_section:
            return itinerary_items
        
        # Find all itinerary day items within the itinerary section only
        day_items = itinerary_section.find_all('li', class_='js-ao-common-accordion')
        
        for item in day_items:
            day_info = {}
            
            # Initialize all required keys including empty icon and image
            day_info['icon'] = ""
            day_info['day'] = ""
            day_info['title'] = ""
            day_info['image'] = ""
            day_info['body'] = ""
            
            # Get the day title (e.g., "Day 1: Hanoi")
            title_elem = item.find('div', class_='js-ao-common-accordion__title')
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                # Remove the arrow element text if present
                arrow_elem = title_elem.find('div', class_='ao-common-accordion__arrow')
                if arrow_elem:
                    arrow_text = arrow_elem.get_text(strip=True)
                    title_text = title_text.replace(arrow_text, '').strip()
                
                title_text = self.clean_text(title_text)
                
                # Extract day number and clean title
                day_match = re.search(r'Day (\d+):', title_text)
                if day_match:
                    day_info['day'] = day_match.group(1)
                    # Remove "Day X: " from the title, keeping only what comes after
                    clean_title = re.sub(r'^Day \d+:\s*', '', title_text)
                    day_info['title'] = clean_title
                else:
                    # If it doesn't match "Day X:" pattern, skip this item (likely an inclusion)
                    continue
            else:
                continue
            
            # Get the day content/body
            content_elem = item.find('div', class_='ao-common-accordion__bottom-content')
            if content_elem:
                # Get all paragraphs in the content
                paragraphs = content_elem.find_all('p')
                if paragraphs:
                    body_text = ' '.join([p.get_text(strip=True) for p in paragraphs])
                else:
                    body_text = content_elem.get_text(strip=True)
                body_text = self.clean_text(body_text)
                day_info['body'] = body_text
            
            if day_info['title'] and day_info['body']:
                itinerary_items.append(day_info)
        
        return itinerary_items
    
    def scrape_tour_info(self, url):
        """Main method to scrape tour information"""
        # Parse URL to get base domain
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Check robots.txt (for politeness)
        self.check_robots_txt(base_url)
        
        # Fetch the page
        html_content = self.fetch_page(url)
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Extract summary (itinerary description)
        summary = self.parse_itinerary_description(soup)
        
        # Extract itinerary days
        itinerary = self.parse_itinerary_days(soup)
        
        # Format the result
        result = {
            "summary": summary,
            "itinerary": itinerary
        }
        
        return result


def main():
    st.set_page_config(
        page_title="Tour Scraper",
        page_icon="🗺️",
        layout="wide"
    )
    
    st.title("🗺️ Tour Scraper")
    st.markdown("Extract itinerary information from Flight Centre tour pages")
    
    # Input section
    st.header("Enter Tour URL")
    url = st.text_input(
        "Flight Centre Tour URL",
        placeholder="https://tours.flightcentre.com.au/t/1842",
        help="Enter the full URL of a Flight Centre tour page"
    )
    
    # Validation
    if url and not url.startswith("https://tours.flightcentre.com.au/"):
        st.warning("⚠️ Please enter a valid Flight Centre tour URL")
    
    # Scrape button
    if st.button("🔍 Extract Tour Information", type="primary", disabled=not url):
        if url:
            try:
                with st.spinner("Scraping tour information..."):
                    scraper = TourScraper()
                    result = scraper.scrape_tour_info(url)
                
                # Display results
                st.success("✅ Tour information extracted successfully!")
                
                # Show summary stats
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Days Found", len(result['itinerary']))
                with col2:
                    st.metric("Summary Length", len(result['summary'][0]) if result['summary'][0] else 0)
                
                # Display JSON
                st.header("📄 Extracted Data")
                
                # Pretty formatted JSON
                json_output = json.dumps(result, indent=2, ensure_ascii=False)
                st.code(json_output, language="json")
                
                # Download button
                st.download_button(
                    label="💾 Download JSON",
                    data=json_output,
                    file_name=f"tour_data_{url.split('/')[-1]}.json",
                    mime="application/json"
                )
                
                # Display preview
                st.header("📋 Preview")
                
                # Summary
                st.subheader("Summary")
                if result['summary'][0]:
                    st.write(result['summary'][0])
                else:
                    st.write("No summary found")
                
                # Itinerary
                st.subheader("Itinerary")
                for day in result['itinerary']:
                    with st.expander(f"Day {day['day']}: {day['title']}"):
                        st.write(day['body'])
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("Please check the URL and try again. Make sure it's a valid Flight Centre tour page.")
    
    # Instructions
    st.header("📖 How to Use")
    st.markdown("""
    1. **Find a tour**: Go to [Flight Centre Tours](https://www.flightcentre.com.au/tours) and find a tour you're interested in
    2. **Copy the URL**: Copy the tour page URL (it should look like `https://tours.flightcentre.com.au/t/1842`)
    3. **Paste and extract**: Paste the URL above and click "Extract Tour Information"
    4. **View results**: The extracted data will appear below in JSON format
    5. **Download**: Use the download button to save the JSON file
    """)
    
    st.header("📊 Example URLs")
    example_urls = [
        "https://tours.flightcentre.com.au/t/1842",
        "https://tours.flightcentre.com.au/t/5578",
        "https://tours.flightcentre.com.au/t/2156"
    ]
    
    for i, example_url in enumerate(example_urls, 1):
        if st.button(f"Try Example {i}: {example_url}", key=f"example_{i}"):
            st.rerun()


if __name__ == "__main__":
    main()