from flask import Flask, request, jsonify, render_template, send_file
import requests
import csv
import io
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json
from flask_cors import CORS
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

def normalize_domain(url):
    """Extracts and returns only the domain from any given URL format."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url  # Ensure proper URL format if not provided
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith("www."):
        domain = domain[4:]  # Remove 'www.' if present
    return domain


def get_seo_data(domain):
    """Fetch and parse SEO data for a given domain."""
    # Generate Target URL
    url = f"https://tools.trafficthinktank.com/website-traffic-checker?q={domain}"

    # Headers to mimic a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/"
    }

    # Send a GET request
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code != 200:
        return {"error": f"Failed to retrieve the page. Status Code: {response.status_code}"}, None

    # Parse the HTML content
    soup = BeautifulSoup(response.text, "html.parser")

    def extract_metric(metric_name):
        """Helper function to extract a metric from the page."""
        metric_section = soup.find("p", string=metric_name)
        if metric_section:
            value_tag = metric_section.find_next_sibling("p")
            if value_tag and value_tag.find("a"):
                return value_tag.find("a").text.strip()
        return "Not Found"

    # Extract required metrics
    organic_traffic = extract_metric("Organic Search Traffic")
    traffic_value = extract_metric("Traffic Value")
    authority_score = extract_metric("Authority Score")
    visits = extract_metric("Visits")
    pages_per_visit = extract_metric("Pages / Visit")
    avg_visit_duration = extract_metric("Avg. Visit Duration")
    bounce_rate = extract_metric("Bounce Rate")
    total_referring_domains = extract_metric("Total Referring Domains")
    ranking_keywords = extract_metric("Ranking Keywords")

    # Extract Backlinks
    backlinks = []
    backlinks_section = soup.find("h3", string="Backlinks")
    if backlinks_section:
        backlinks_table = backlinks_section.find_next("table")
        if backlinks_table:
            rows = backlinks_table.find_all("tr")[1:]  # Skip header row
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 4:
                    source_url = cols[0].find("a")["href"].strip()
                    target_url = cols[0].find_all("a")[-1]["href"].strip()
                    anchor_text = cols[1].text.strip()
                    follow_type = cols[2].text.strip()
                    backlinks.append({
                        "source_url": source_url,
                        "target_url": target_url,
                        "anchor_text": anchor_text,
                        "follow_type": follow_type
                    })

    # Extract Top Pages (URLs, Traffic %, Keywords)
    top_pages = []
    top_pages_section = soup.find("h3", string="Top Pages")
    if top_pages_section:
        top_pages_table = top_pages_section.find_next("table")
        if top_pages_table:
            rows = top_pages_table.find_all("tr")[1:]  # Skip header row
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    page_url = cols[0].find("a").text.strip()
                    traffic_percentage = cols[1].text.strip()
                    keywords = cols[2].text.strip()
                    top_pages.append({
                        "page_url": page_url,
                        "traffic_percentage": traffic_percentage,
                        "keywords": keywords
                    })

    # Extract Main Organic Competitors
    competitors = []
    competitors_section = soup.find("h3", string="Main Organic Competitors")
    if competitors_section:
        competitors_table = competitors_section.find_next("table")
        if competitors_table:
            rows = competitors_table.find_all("tr")[1:]  # Skip header row
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    domain = cols[0].text.strip()
                    com_keywords = cols[1].text.strip()
                    com_level = cols[2].text.strip()
                    competitors.append({
                        "domain": domain,
                        "common_keywords": com_keywords,
                        "competition_level": com_level
                    })

    # Extract Top Ranking Keywords with additional details
    top_keywords = []
    keyword_table = soup.find("div", class_="table")
    if keyword_table:
        rows = keyword_table.find_all("tr")[1:]  # Skip header row
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 8:  # Ensure there are enough columns
                keyword = cols[0].text.strip()
                rank_data = cols[1]
                movement_icon = rank_data.find("svg", {"xmlns": "http://www.w3.org/2000/svg"})

                rank = cols[1].text.strip()
                traffic_percentage = cols[2].text.strip()
                volume = cols[3].text.strip()
                kd_percentage = cols[4].text.strip()
                cpc = cols[5].text.strip()
                num_results = cols[6].text.strip()
                search_trend = cols[7].text.strip()
                top_keywords.append({
                    "keyword": keyword,
                    "rank": rank,
                    "traffic_percentage": traffic_percentage,
                    "volume": volume,
                    "kd_percentage": kd_percentage,
                    "cpc": cpc,
                    "num_results": num_results,
                    "search_trend": search_trend
                })

    # Create JSON result
    result = {
        "domain": domain,
        "metrics": {
            "organic_traffic": organic_traffic,
            "traffic_value": traffic_value,
            "authority_score": authority_score,
            "visits": visits,
            "pages_per_visit": pages_per_visit,
            "avg_visit_duration": avg_visit_duration,
            "bounce_rate": bounce_rate,
            "total_referring_domains": total_referring_domains,
            "ranking_keywords": ranking_keywords
        },
        "top_keywords": top_keywords,
        "backlinks": backlinks,
        "competitors": competitors,
        "top_pages": top_pages
    }

    # Generate CSV data
    csv_data = io.StringIO()
    writer = csv.writer(csv_data)

    # Write Basic Metrics
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Organic Search Traffic", organic_traffic])
    writer.writerow(["Traffic Value", traffic_value])
    writer.writerow(["Authority Score", authority_score])
    writer.writerow(["Visits", visits])
    writer.writerow(["Pages per Visit", pages_per_visit])
    writer.writerow(["Avg. Visit Duration", avg_visit_duration])
    writer.writerow(["Bounce Rate", bounce_rate])
    writer.writerow(["Total Referring Domains", total_referring_domains])
    writer.writerow(["Ranking Keywords", ranking_keywords])

    # Write Top Ranking Keywords with additional details
    writer.writerow([])
    writer.writerow(["Top Ranking Keywords"])
    writer.writerow(["Keyword", "Rank", "Traffic %", "Volume", "KD %", "CPC (USD)", "# of Results", "Search Trend"])
    for kw in top_keywords:
        writer.writerow([kw["keyword"], kw["rank"], kw["traffic_percentage"], kw["volume"],
                         kw["kd_percentage"], kw["cpc"], kw["num_results"], kw["search_trend"]])

    # Write Backlinks
    writer.writerow([])
    writer.writerow(["Backlinks"])
    writer.writerow(["Source URL", "Target URL", "Anchor Text", "Follow Type"])
    for bl in backlinks:
        writer.writerow([bl["source_url"], bl["target_url"], bl["anchor_text"], bl["follow_type"]])

    # Write Main Organic Competitors
    writer.writerow([])
    writer.writerow(["Main Organic Competitors"])
    writer.writerow(["Domain", "Common Keywords", "Competition Level"])
    for comp in competitors:
        writer.writerow([comp["domain"], comp["common_keywords"], comp["competition_level"]])

    # Write Top Pages
    writer.writerow([])
    writer.writerow(["Top Pages"])
    writer.writerow(["URL", "Traffic %", "Keywords"])
    for tp in top_pages:
        writer.writerow([tp["page_url"], tp["traffic_percentage"], tp["keywords"]])

    return result, csv_data.getvalue()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/seo-data', methods=['GET'])
def fetch_seo_data():
    url = request.args.get('url', '')
    if not url:
        return jsonify({"error": "No URL provided. Please include a 'url' parameter."}), 400

    # Normalize domain
    domain = normalize_domain(url)

    # Get SEO data
    data, _ = get_seo_data(domain)

    if "error" in data:
        return jsonify(data), 500

    return jsonify(data)


@app.route('/api/seo-data/csv', methods=['GET'])
def fetch_seo_data_csv():
    url = request.args.get('url', '')
    if not url:
        return jsonify({"error": "No URL provided. Please include a 'url' parameter."}), 400

    # Normalize domain
    domain = normalize_domain(url)

    # Get SEO data
    data, csv_data = get_seo_data(domain)

    if "error" in data:
        return jsonify(data), 500

    # Return CSV as file download
    output = io.StringIO()
    output.write(csv_data)
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{domain}_seo_data.csv'
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
