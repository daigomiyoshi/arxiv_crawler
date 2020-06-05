import pandas as pd
import feedparser
from urllib.parse import urlencode
import datetime
from dateutil.relativedelta import relativedelta
from googletrans import Translator


def main():
	root_url = 'http://export.arxiv.org/api/'
	keywords = ['cat: stat.ML']
	start = 0
	max_results = 500
	sort_by = 'submittedDate'
	sort_order = "descending"
	days = 20
	prune = True
	debug = False

	for keyword in keywords:
    	arxiv_lists = make_list(root_url, keyword, prune, start,
    	                        max_results, sort_by, sort_order, days, debug)

    title, summary, published, arxiv_url, pdf_url = translate(arxiv_lists)
    translated_arxiv_pd = pd.DataFrame({
	    'title': title, 
	    'summary': summary,
	    'published': published,
	    'arxiv_url': arxiv_url,
	    'pdf_url': pdf_url
	})
	translated_arxiv_pd.to_csv('translated_arxiv_v0.csv', index=False, encoding='utf_8_sig')


def make_list(root_url, keyword, prune, start, max_results, sort_by, sort_order, days, debug):
    results = query(
        root_url = root_url,
        search_query=keyword,
        prune=prune,
        start=start,
        max_results=max_results,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return select_recent_papers(from_papers_list=results, days=days, debug=debug)


def query(root_url, search_query, prune, start, max_results, sort_by, sort_order):
    url_args = urlencode({"search_query": search_query,
                                          "start": start,
                                          "max_results": max_results,
                                          "sortBy": sort_by,
                                          "sortOrder": sort_order})
    results = feedparser.parse(root_url + 'query?' + url_args)
    if results.get('status') != 200:
        raise Exception(
            "HTTP Error " + str(results.get('status', 'no status')) + " in query")
    else:
        results = results['entries']
    for result in results:
        modify_query_result(result)
        if prune:
            prune_query_result(result)
    return results


def modify_query_result(result):
    result['pdf_url'] = None
    for link in result['links']:
        if 'title' in link and link['title'] == 'pdf':
            result['pdf_url'] = link['href']
    result['affiliation'] = result.pop('arxiv_affiliation', 'None')
    result['arxiv_url'] = result.pop('link')
    result['title'] = result['title'].rstrip('\n')
    result['summary'] = result['summary'].rstrip('\n')
    result['authors'] = [d['name'] for d in result['authors']]
    if 'arxiv_comment' in result:
        result['arxiv_comment'] = result['arxiv_comment'].rstrip('\n')
    else:
        result['arxiv_comment'] = None
    if 'arxiv_journal_ref' in result:
        result['journal_reference'] = result.pop('arxiv_journal_ref')
    else:
        result['journal_reference'] = None
    if 'arxiv_doi' in result:
        result['doi'] = result.pop('arxiv_doi')
    else:
        result['doi'] = None
        

def prune_query_result(result):
    prune_keys = ['updated_parsed',
                              'arxiv_primary_category',
                              'summary_detail',
                              'author',
                              'author_detail',
                              'links',
                              'guidislink',
                              'title_detail',
                              'tags',
                              'id']
    for key in prune_keys:
        try:
            del result[key]
        except KeyError:
            pass


def select_recent_papers(from_papers_list, days, debug):
    today = datetime.datetime.today()
    utc_today = today - relativedelta(hours=9)

    from_when = utc_today - relativedelta(days=days)
    to_when = utc_today

    if debug:
        print('JST: ', today)
        print('UTC_from: ', from_when)
        print('UTC_to  : ', to_when)
        print()
        print('recent papers\' timestamps are like below:')
        for paper in from_papers_list:
            print(paper['published'])

    return list(filter(lambda x: condition_to_select_papers(x, from_when, to_when), from_papers_list))


def condition_to_select_papers(paper, from_when, to_when):
    return from_when <= datetime.datetime(*paper['published_parsed'][:6]) < to_when


def translate(result):
    translator = Translator()
    title = []
    summary = []
    title_and_summary = []
    result_title = []
    result_summary = []
    title = list(map(lambda x: x['title'].replace('\n', ' '), result))
    summary = list(map(lambda x: x['summary'].replace('\n', ' '), result))
    published = list(map(lambda x: x['published'], result))
    arxiv_url = list(map(lambda x: x['arxiv_url'], result))
    pdf_url = list(map(lambda x: x['pdf_url'], result))

    for i in zip(title, summary):
        title_and_summary.append(i)

    for i in range(len(title_and_summary)):
        tas = title_and_summary[i]
        text_title =  tas[0]
        text_summary = tas[1]
        translate_title = translator.translate(text_title, dest='ja', src='en')
        translate_summary = translator.translate(text_summary, dest='ja', src='en')
        result_title.append(translate_title.text)
        result_summary.append(translate_summary.text)
        print("No.{}, title:{}".format(i, translate_title.text))
    result_title = list(map(lambda x: x.replace('\n\xa0\xa0', ':'), result_title))
    result_summary = list(map(lambda x: x.replace('\n\xa0\xa0', ':'), result_summary))

    return title, summary, published, arxiv_url, pdf_url

if __name__ == '__main__':
    main()
