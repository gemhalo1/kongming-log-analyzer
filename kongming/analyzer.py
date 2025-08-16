import json

from .constants import CLEAN_CONTEXT_MAGIC_STRING

def is_json_seriable(x):
    try:
        _ = json.dumps(x)
        return True
    except:
        return False


class KongmingLogAnalyzer(object):
    def __init__(self):
        pass

    def shall_ignore(self, record):
        src = record['_source']

        # ignore ping frames
        if src.get("message") in ["try to send  ping frame", "healthExamination"]:
            return True

        if 'Duplicate contact data for device:' in src.get("message", ''):
            return True

        if 'tags' in src and '_jsonparsefailure' in src['tags']:
            return True

        return False

    def pre_process_record(self, record):
        src = record['_source']

        laname = src.get('laname', '')

        for remove_key in ['_ignored', '_score', '_type', 'sort']:
            if remove_key in record:
                del record[remove_key]

        for remove_key in ['messageobj', 'log', 'input', 'lmt', 'level', 'fields', 'class', 'lblpl', 'lnode', 'lenv', 'type', 'sort']:
            if remove_key in src:
                del src[remove_key]

        if 'message' in src and isinstance(src['message'], str):
            try:
                msg = src['message']

                if ',---headers' in msg:
                    splits = msg.split(',---headers')
                    msg = splits[0]
                    src['message'] = msg
                    src['headers'] = splits[1]

                    try:
                        src['headers'] = eval(splits[1])
                    except:
                        pass

                for prefix in ['调用魅族服务结束，返回结果:',
                            'asr-result:',
                            'upload request:',
                            'upload result:',
                            'receive request:',
                            'start normalize-slot:',
                            'summary request:',
                            'deal request:',
                            'post  body ',
                            ' nlp _result:',
                            'todos request:',
                            '数据库中 asrRecord:',
                            "合规账号查询结果响应:",
                            '收到数据',
                            '合规文本请求',
                            '合规文本响应',
                            '合规图片响应',
                            'tts 请求 数据',
                            'answers  response:',
                            'answer request params:',
                            'start request:',
                            'matched normalize-slot:',
                            'received client request text: ',
                            'current instruction info is:',
                            'global_ml_response:',
                            'upload stkscontext request:',
                            'global request :metadata ',
                            'global_rule_response: ',
                            'longtail_rule_response: ',
                            'hinter request params:',
                            'received speech vad0 info, send to client vad mid result, msg: ',
                            'say visible v2 start, request:',
                            'speech client onMessage received: ']:
                    if msg.startswith(prefix):
                        msg = msg[len(prefix):]
                        src['message.prefix'] = prefix
                        break
                src['message'] = msg

                for postfix in [',从发首包到收到结果耗时:', 
                                ',version is:', 
                                ',domain:weather',
                                '-- 耗时:',
                                ' 耗时:',
                                ',耗时:',
                                ',耗时：',
                                ', latency=',
                                ',url:',
                                ',session:',
                                ',url:http://myvu-rule.xr-nbs.svc.cluster.local']:
                    if postfix in msg:
                        pos = msg.index(postfix)
                        src['message.postfix'] = msg[pos:]
                        msg = msg[:pos]

                        break

                src['message'] = msg

                msg = json.loads(msg)

                if type(msg) == str:
                    # 可能是又嵌套了一层的json, 例如central-manager的合规文本响应
                    try:
                        msg = json.loads(msg)
                    except Exception as e:
                        print(e)

                if isinstance(msg, dict):
                    x = msg.get('msg')
                    if isinstance(x, str):
                        if '<HTTPStatus.OK: 200>' in x:
                            x = x.replace('<HTTPStatus.OK: 200>', '200')
                        if '<Response [200]>' in x:
                            x = x.replace('<Response [200]>', '200')

                        msg['msg'] = x

                        if not x.startswith('parse request'): # badcase from laname:'dlg-dm-glasses'
                            for prefix in ['response: ',
                                            'got query embedding: ', 
                                            'tokenizer inputs: ',
                                            'load profile succeed: ',
                                            'Get request: ',
                                            'Chitchat Skill response: ',
                                            'multi_answers：',
                                            'Chitchat Parse response:',
                                            'past context info: ',
                                            'base multi parse request, nlu_info: ',
                                            'save profile to redis succeed! profile info: ',
                                            "{'get_dify_global_todos response: 200, text:",
                                        ]:
                                if x.startswith(prefix):
                                    x = x[len(prefix):]

                                    if prefix == "{'get_dify_global_todos response: 200, text:":
                                        x = x[:-2]

                                    msg['msg'] = x
                                    msg['msg.prefix'] = prefix

                                    break

                            for postfix in ['， new_key=',
                                            ', business_state:']:
                                if postfix in x:
                                    pos = x.index(postfix)
                                    msg['msg.postfix'] = x[pos:]
                                    x = x[:pos]
                                    msg['msg'] = x
                                    break

                            try:
                                x = eval(x)

                                if is_json_seriable(x):
                                    msg['msg'] = x
                            except Exception as e:
                                # print('++++', x)
                                # print('===> ', e)
                                pass

                    for key in ['result']:
                        try:
                            msg[key] = json.loads(msg[key])
                        except:
                            pass

                src['message'] = msg
            except Exception as e:
                pass

        for key in ['asr-recognize-start',
                    'asr-recognize-result',
                    'api-server-request',
                    'api-server-response', 
                    'central-nlp-request',
                    'central-nlp-response',
                    'central-hinter-request',
                    'central-hinter-response',
                    'central-answer-request',
                    'central-answer-response'
                    ]:
            try:
                src[key] = json.loads(src[key])
            except:
                pass

        return record

    def get_trace_id(self, record):
        src = record['_source']

        laname = src.get('laname', '')
        trace_id = src.get('trace_id') or src.get('traceId')
        if not trace_id or trace_id.startswith('-'):
            if 'message' in src and isinstance(src['message'], dict):
                trace_id = src['message'].get('trace_id') or src['message'].get('traceId')
        try:
            if laname == 'central-manager' and isinstance(src.get('message'), dict) and 'metadata' in src['message'] and 'terminalTraceId' in src['message']['metadata']:
                trace_id = src['message']['metadata']['terminalTraceId']
            elif laname == 'asr-server' and trace_id is None or trace_id.startswith('-') and 'message' in src:
                trace_id = src['message'].get('requestId') or src['message'].get('request_id')
        except Exception as e:
            print(e)

        return trace_id or ''

    def group_by_traceid(self, records):
        ignored = []
        groups = {}
    
        record_id = 0

        for record in records:
            if self.shall_ignore(record):
                ignored.append(record_id)
            else:
                record = self.pre_process_record(record)

                src = record['_source']
                trace_id = self.get_trace_id(record) #  src.get('trace_id') or src.get('traceId') or ''

                if trace_id not in groups:
                    groups[trace_id] = {
                        'records': [],
                        'timestamp': src.get('ltime', '')
                    }

                groups[trace_id]['records'].append(record_id)

            record_id += 1

        for group in groups.values():
            for record_id in group['records']:
                record = records[record_id]
                src = record['_source']
                laname = src.get('laname', '')

                # TODO: 应该从centrao-manager获取query数据．因为在纯大模型请求的时候，api-server会收到特殊的"...)(%$$)"而不是真实请求
                if laname == 'api-server' and 'api-server-request' in src:
                    q_text = src['api-server-request']['payload']['q']
                    group['q'] = q_text

        return groups, ignored

    def analyze(self, records, out_file):
        record_groups, record_ignored = self.group_by_traceid(records)

        with open(out_file, mode='w', encoding='utf-8') as f_out:
            for _, trace_id in enumerate(record_groups):
                group = record_groups[trace_id]

                if 'q' in group:
                    f_out.write(f'# {group["timestamp"]} - {trace_id} : {group["q"] if group["q"] != CLEAN_CONTEXT_MAGIC_STRING else "<清除上下文>"}\n')
                else:
                    f_out.write(f'# {group["timestamp"]} - {trace_id}\n')

                for record_id in group['records']:
                    record = records[record_id]

                    src = record['_source']

                    ltime = src.get('ltime', '')
                    message = src.get('message', {})

                    # get laname
                    laname = src.get('laname', '')
                    if not laname:
                        if isinstance(message, str):
                            if message.startswith('可见即可说') or message.startswith('say visible'):
                                laname = 'say-visible'
                    if not laname:
                        if 'message.prefix' in src:
                            if src['message.prefix'].startswith('可见即可说') or src['message.prefix'].startswith('say visible'):
                                laname = 'say-visible'
                    if not laname or laname == 'None':
                        if 'modules' in src:
                            laname = src['modules'].split(':')[0]
                    if not laname:
                        laname = '?'

                    # write the title
                    f_out.write(f'\n## ［{record_id}］ -  [{laname}]')
                    if laname == 'api-server':
                        if 'api-server-request' in src:
                            f_out.write(f' 从客户端接收请求')
                        elif 'api-server-response' in src:
                            f_out.write(f' 向客户端输出结果')
                    elif laname == 'asr-server':
                        if 'asr-recognize-result' in src:
                            f_out.write(f' 最终识别结果')
                        elif isinstance(message, dict) and 'event' in message:
                            if message['event'] == 'asr_result_success':
                                f_out.write(f' 中间识别结果')
                    elif laname == 'central-manager':
                        if 'central-hinter-request' in src:
                            f_out.write(f' 请求提示问题')
                        if 'central-hinter-response' in src:
                            f_out.write(f' 响应提示问题')
                        if 'central-answer-response' in src:
                            f_out.write(f' 返回大模型结果')
                        if 'central-answer-request' in src:
                            f_out.write(f' 收到大模型请求')
                        if 'central-nlp-request' in src:
                            f_out.write(f' NLP请求')
                            if isinstance(src['central-nlp-request'], dict) and isinstance(src['central-nlp-request'].get('payload'), dict):
                                q = src['central-nlp-request']['payload'].get('q')
                                if q == CLEAN_CONTEXT_MAGIC_STRING:
                                    f_out.write(f' <清除上下文>')
                                elif q is not None:
                                    f_out.write(f' "{q}"')
                        if 'central-nlp-response' in src:
                            f_out.write(f' NLP响应')
                        if isinstance(message, str) and 'answer 连接成功' in message:
                            f_out.write(f' 建立连接')
                        if "message.prefix" in src:
                            prefix = src['message.prefix']
                            if '合规文本请求' in prefix:
                                f_out.write(f' 合规文本请求')
                            if 'answer request params' in prefix:
                                f_out.write(f' 大模型请求参数')
                            if '合规文本响应' in prefix:
                                f_out.write(f' 合规文本响应')
                            if '合规图片响应' in prefix:
                                f_out.write(f' 合规图片响应')
                            if 'hinter request params' in prefix:
                                f_out.write(f' 提示问题请求参数')
                            if 'hinter  response:' in prefix:
                                f_out.write(f' 响应提示问题')
                            if 'post  body' in prefix:
                                f_out.write(f' 发送消息体')
                                if isinstance(message, dict) and isinstance(message.get('payload'), dict):
                                    q = message['payload'].get('q')
                                    if q == CLEAN_CONTEXT_MAGIC_STRING:
                                        f_out.write(f' <清除上下文>')
                                    elif q is not None:
                                        f_out.write(f' "{q}"')
                            if '收到数据' in prefix:
                                f_out.write(f' 收到数据')
                            if 'receive request:' in prefix:
                                f_out.write(f' 收到请求')
                            if 'answers  response' in prefix:
                                f_out.write(f' 大模型响应消息')
                                if isinstance(message, dict) and 'base_status' in message:
                                    if message['base_status'] in [2]:
                                        f_out.write(f' [最终结果]')
                                    else:
                                        f_out.write(f' [中间结果]')
                        if isinstance(message, dict):
                            if isinstance(message.get('services'), list):
                                service_types = []
                                for x in message['services']:
                                    service_types.append(x['type'])
                                f_out.write(f' {"+".join(service_types)}')
                            elif 'type' in message:
                                f_out.write(f' {message["type"]}')
                    elif laname == 'cc-talk':
                        if isinstance(message, dict) and 'cc-talk' in message:
                            x = message['cc-talk']

                            if 'brpc' in x:
                                if x['brpc'] == 'request':
                                    f_out.write(f" 请求 {x['instance']}::{x['method_name']}")
                                elif x['brpc'] == 'response':
                                    f_out.write(f" 响应 {x['instance']}")
                            if 'title' in x:
                                if x['title'] == 'return response':
                                    f_out.write(f" 返回NLU结果")
                                elif x['title'] == 'new request':
                                    f_out.write(f" 收到请求")
                        elif isinstance(message, str):
                            if 'AppendDebugInfo' in message:
                                f_out.write(f" 附加调试信息")
                    elif laname == 'nlp-intent-prejudge':
                        if isinstance(message, str):
                            if message.startswith('domain judge strategy result: modelSelectedDomains='):
                                f_out.write(f" 预判结果")
                            elif message.startswith('begin ml prejudge'):
                                f_out.write(f" 开始模型预判")
                    elif laname == 'nlp-intent-arbitrator':
                        if isinstance(message, str) and message.startswith('arbitrator model result'):
                            f_out.write(f" 仲裁结果")
                    elif laname == 'domain-service-cc-qa' and isinstance(message, dict) and isinstance(message.get('msg'), str):
                        msg = message['msg']
                        if msg.startswith('Starting _predict_with_model'):
                            f_out.write(f" 开始用模型预测subtopic")
                        elif 'pre_subtopic:' in msg:
                            f_out.write(f" 模型预测subtopic的结果")
                    elif laname == 'xr_llms_service_qa' and isinstance(message, dict):
                        msg = message['msg']
                        if isinstance(msg, dict):
                            if 'Final answer' in msg:
                                f_out.write(f" 输出大模型结果")
                            elif 'answer request, query' in msg:
                                f_out.write(f" 收到大模型请求")
                        elif isinstance(msg, str):
                            if 'system_prompt' in msg:
                                f_out.write(f" 系统提示词")
                            elif "'base_status': 1" in msg:
                                f_out.write(f" 输出流式结果")

                        modules = message['modules']
                        if isinstance(modules, str):
                            if 'utils.py:save_profile_to_redis' in modules:
                                f_out.write(f" 保存上下文")

                    elif laname == 'xr_llms_service_question' and isinstance(message, dict) and isinstance(message.get('msg'), dict):
                        msg = message['msg']
                        if 'question request' in msg:
                            f_out.write(f" 收到大模型请求")

                    f_out.write('\n')

                    if trace_id in ['MeiZuWeatherServiceTraceId', 'WeatherControllerTraceId']:
                        try:
                            message = json.dumps(message, ensure_ascii=False, indent=2)
                        except Exception as e:
                            pass
                        f_out.write(f"### message\n```json\n{message}\n```\n")
                    elif isinstance(message, str) and 'final response: ' in message:
                        pos = message.index(',parameters:')
                        inner_msg = '\n- '.join(message[:pos].split(','))
                        f_out.write(f"\n### message\n{inner_msg}")

                        parameters = json.loads(message[pos+len(',parameters:'):])
                        if 'result_' in parameters:
                            parameters['result_'] = json.loads(parameters['result_'])
                        f_out.write(f"\n### parameters\n```json\n{json.dumps(parameters, ensure_ascii=False, indent=2)}\n```\n")
                    else:
                        f_out.write(f'\n```json\n{json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True)}\n```\n')

