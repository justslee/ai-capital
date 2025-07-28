from sec_downloader import Downloader
import sec_parser as sp
import warnings

def parse_filing():
    dl = Downloader("AI-Capital", "justinlee627@gmail.com")
    html = dl.get_filing_html(ticker="AAPL", form="10-K")
    parser = sp.Edgar10QParser()

    # Parse the HTML using Edgar10KParser
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Invalid section type for")
        elements = parser.parse(html)
    
    tree: sp.SemanticTree = sp.TreeBuilder().build(elements)

    # Print the full tree structure
    print("Full Tree Structure:")
    print("=" * 80)
    demo_output: str = sp.render(tree)
    print(demo_output)
    
    # Print TextElements specifically
    print("\nText Elements:")
    print("=" * 80)
    for node in tree.nodes:
        if "TextElement" in str(node):
            print(f"Found TextElement:")
            print("-" * 40)
            print(sp.render(node))
            print("=" * 80)

if __name__ == "__main__":
    parse_filing()