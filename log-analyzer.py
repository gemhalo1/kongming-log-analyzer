from typing import List
from pprint import pprint
from kongming.analyzer import KongmingLogAnalyzer
from kongming.elk import KongmingELKServer, NlpRequest
from kongming.html import print_nlp_request_html
from kongming.console import print_nlp_request_table

if __name__ == '__main__':
    server = KongmingELKServer()
    analyzer = KongmingLogAnalyzer()

    # records = server.query_by_trace_id('EE37E429-1B82-45CF-85AC-C7AFC7823154', pagesize=100, out_file="3.json")
    # analyzer.analyze(records, "3.md")

    # records = server.query_by_phrase('terminalTraceId', 
    #                                  terms={"laname.keyword": "central-manager"}, 
    #                                  timestamp_begin='2025-08-15',
    #                                  size=1000, 
    #                                  pagesize=200, 
    #                                  out_file="logs/xxx.json")
    # analyzer.analyze(records, "logs/xxx.md")

    records, nlp_requests = server.query_nlp_request( 
                                     timestamp_begin='2025-08-12',
                                     timestamp_end='2025-08-16',
                                     size=300, 
                                     pagesize=1000, 
                                     out_file="logs/0812-nlp.json"
    )
    analyzer.analyze(records, "logs/0815-nlp.md")
    print_nlp_request_html(nlp_requests, "logs/nlp_requests_0812.html")

    print_nlp_request_table(nlp_requests)
