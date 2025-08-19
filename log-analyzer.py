from kongming.analyzer import KongmingLogAnalyzer
from kongming.elk import KongmingELKServer
# from kongming.html import print_nlp_request_html
from kongming.console import print_dialog_round_table
from kongming.model import DialogLogFilter
from kongming.elk import KongmingEnvironmentType

def analyze_trace_id(trace_id:str, env:KongmingEnvironmentType):
    records, rounds = server.query_dialog_by_trace_id(trace_id=trace_id,env=env, out_file=f"logs/{trace_id}.json")
    if records:
        print_dialog_round_table(rounds)
        analyzer.analyze(records, f"logs/{trace_id}.md")
    else:
        print('not found')

## 我的 glassDeviceId: 78783359051b2d81f6a9cb923c81838da8214724

if __name__ == '__main__':
    server = KongmingELKServer(env='uat')
    analyzer = KongmingLogAnalyzer()

    # records = server.query_by_time_range(timestamp_begin='2025-08-10T11:34:00',
    #                                      timestamp_end='2025-08-10T11:36:00',
    #                                      size=10000, 
    #                                      pagesize=1000,
    #                                      out_file='logs/1111.json')
    # analyzer.analyze(records, f"logs/1111.md")


    # analyze_trace_id('E5FE48B7-EF60-44FA-B296-8B5C6F90A6AB', env='uat')
    # analyze_trace_id('8B87AA93-0315-4F0B-AA63-7AECC2DB550D',env='uat')
    # analyze_trace_id('AAFDD6D7-FA54-4C4A-A2EC-EDA2E13BC771')
    # analyze_trace_id('d67c050e-17b4-4a61-a274-69b6ab41a47c')

    # analyze_trace_id('2eec269b-9ced-4d77-9cfe-737129d782ea')
    # analyze_trace_id('ca56cec7-220a-4c65-b551-ea98c5598fa6')
    # analyze_trace_id('44594e4c-1cf3-4a48-a3c3-fef1940d19bd')
    # analyze_trace_id('118eeecc-0ea0-4dd6-b7ee-baed72bc3392')
    

    # records = server.query_by_phrase('terminalTraceId', 
    #                                  terms={"laname.keyword": "central-manager"}, 
    #                                  timestamp_begin='2025-08-15',
    #                                  size=1000, 
    #                                  pagesize=200, 
    #                                  out_file="logs/xxx.json")
    # analyzer.analyze(records, "logs/xxx.md")



    from kongming.model import DialogLogFilter
    records, rounds = server.query_dialogs(
        DialogLogFilter(#  id_type='glassDeviceId', 
                        #  id_value='2c6f4e0117f5',
                        timestamp_begin='2025-08-15T00:00:00.000',
                        timestamp_end='2025-08-20T00:00:00.000',
        ),
        size=2000,
        env='uat',
        out_file='logs/uat-0815-2000.json')
    from kongming.console import print_dialog_round_table
    print_dialog_round_table(rounds)

    from kongming.excel import print_dialog_round_to_excel
    print_dialog_round_to_excel(rounds, 'logs/uat-0815-2000.xlsx')

    # analyzer.analyze(records, "logs/uat-dialogs-0818.md")
    # for round in rounds:
    #     print(round.model_dump_json(indent=2))
    #     print('-------')
