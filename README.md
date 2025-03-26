# ➤ travel-advisories

This project maintains an unofficial history of travel advisories from various governments.

This is stored as git history, so that you can see changes over time via the git history. You can learn more about this approach, often called "git scraping" by reading [this blog entry by Simon Willison](https://simonwillison.net/2020/Oct/9/git-scraping/). In particular, Simon developed a tool called [git-history](https://github.com/simonw/git-history) that allows analyzing this history in an easy way.


## Currently tracking


- 🇨🇦 Canada, summary data ([CSV](https://github.com/marcolussetti/travel-advisories/blob/main/canada_summary.csv)<sup>[history](https://github.com/marcolussetti/travel-advisories/commits/main/canada_summary.csv)</sup>, [JSON](https://github.com/marcolussetti/travel-advisories/blob/main/canada_summary.json)<sup>[history](https://github.com/marcolussetti/travel-advisories/commits/main/canada_summary.json)</sup>)
    - [Detailed data](https://github.com/marcolussetti/travel-advisories/tree/main/canada) (<sup>[history](https://github.com/marcolussetti/travel-advisories/commits/main/canada)</sup>)
    - [![canada - fetch latest travel-advisories data](https://github.com/marcolussetti/travel-advisories/actions/workflows/canada.yml/badge.svg)](https://github.com/marcolussetti/travel-advisories/actions/workflows/canada.yml)
- 🇮🇪 Ireland, summary data ([CSV](https://github.com/marcolussetti/travel-advisories/blob/main/ireland_summary.csv)<sup>[history](https://github.com/marcolussetti/travel-advisories/commits/main/uireland_summary.csv)</sup>, [JSON](https://github.com/marcolussetti/travel-advisories/blob/main/ireland_summary.json)<sup>[history](https://github.com/marcolussetti/travel-advisories/commits/main/ireland_summary.json)</sup>)
    - [Detailed data](https://github.com/marcolussetti/travel-advisories/tree/main/ireland) (<sup>[history](https://github.com/marcolussetti/travel-advisories/commits/main/ireland)</sup>)
    - [![ireland - fetch latest travel-advisories data](https://github.com/marcolussetti/travel-advisories/actions/workflows/ireland.yml/badge.svg)](https://github.com/marcolussetti/travel-advisories/actions/workflows/ireland.yml)
- 🇬🇧 United Kingdom, summary data ([CSV](https://github.com/marcolussetti/travel-advisories/blob/main/unitedkingdom_summary.csv)<sup>[history](https://github.com/marcolussetti/travel-advisories/commits/main/unitedkingdom_summary.csv)</sup>, [JSON](https://github.com/marcolussetti/travel-advisories/blob/main/unitedkingdom_summary.json)<sup>[history](https://github.com/marcolussetti/travel-advisories/commits/main/unitedkingdom_summary.json)</sup>)
    - [Detailed data](https://github.com/marcolussetti/travel-advisories/tree/main/kingdom) (<sup>[history](https://github.com/marcolussetti/travel-advisories/commits/main/unitedkingdom)</sup>)
    - [![unitedkingdom - fetch latest travel-advisories data](https://github.com/marcolussetti/travel-advisories/actions/workflows/unitedkingdom.yml/badge.svg)](https://github.com/marcolussetti/travel-advisories/actions/workflows/unitedkingdom.yml)
- 🇺🇸 United States, summary data ([CSV](https://github.com/marcolussetti/travel-advisories/blob/main/unitedstates_summary.csv)<sup>[history](https://github.com/marcolussetti/travel-advisories/commits/main/unitedstates_summary.csv)</sup>, [JSON](https://github.com/marcolussetti/travel-advisories/blob/main/unitedstates_summary.json)<sup>[history](https://github.com/marcolussetti/travel-advisories/commits/main/unitedstates_summary.json)</sup>)
    - [![unitedstates - fetch latest travel-advisories data](https://github.com/marcolussetti/travel-advisories/actions/workflows/unitedstates.yml/badge.svg)](https://github.com/marcolussetti/travel-advisories/actions/workflows/unitedstates.yml)


## Next Steps

We're planning on:

- [ ] Adding detailed advisories from the United States
- [ ] Adding advisories from Australia
- [ ] Adding advisories from Italy
- [ ] Adding advisories from France
- [ ] Visualize travel advisories with standardized levels into a heatmap
- [ ] Visualzie travel advisory history as a heatmap
