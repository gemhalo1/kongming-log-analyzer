from typing import List
from pprint import pprint
from kongming.analyzer import KongmingLogAnalyzer
from kongming.elk import KongmingELKServer, NlpRequest
from kongming.html import print_nlp_request_html
from kongming.console import print_nlp_request_table

def analyze_trace_id(trace_id:str):
    records = server.query_by_trace_id(trace_id, size=10000, pagesize=1000, out_file=f"logs/{trace_id}.json")
    analyzer.analyze(records, f"logs/{trace_id}.md")

if __name__ == '__main__':
    server = KongmingELKServer()
    analyzer = KongmingLogAnalyzer()

    # analyze_trace_id('2eec269b-9ced-4d77-9cfe-737129d782ea')
    analyze_trace_id('ca56cec7-220a-4c65-b551-ea98c5598fa6')
    analyze_trace_id('44594e4c-1cf3-4a48-a3c3-fef1940d19bd')
    analyze_trace_id('118eeecc-0ea0-4dd6-b7ee-baed72bc3392')
    

    # records = server.query_by_phrase('terminalTraceId', 
    #                                  terms={"laname.keyword": "central-manager"}, 
    #                                  timestamp_begin='2025-08-15',
    #                                  size=1000, 
    #                                  pagesize=200, 
    #                                  out_file="logs/xxx.json")
    # analyzer.analyze(records, "logs/xxx.md")

    # records, nlp_requests = server.query_nlp_request( 
    #                                  timestamp_begin='2025-08-12',
    #                                  timestamp_end='2025-08-16',
    #                                  size=100, 
    #                                  pagesize=1000, 
    #                                  out_file="logs/0812-nlp.json"
    # )
    # analyzer.analyze(records, "logs/0815-nlp.md")
    # print_nlp_request_html(nlp_requests, "logs/nlp_requests_0812.html")
    # print_nlp_request_table(nlp_requests)
