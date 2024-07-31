"""
pip install pycryptodome requests
"""
import sys
import time
import base64
from typing import List, Union
from requests_toolbelt import MultipartEncoder
import os
import json

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import requests


def aes_encrypt(src: str, secret_key: str, iv: str) -> str:
    if not secret_key:
        raise ValueError("secret_key is empty")

    try:
        # Convert secret_key and iv to bytes
        secret_key = secret_key.encode('utf-8')
        iv = iv.encode('utf-8')

        # Create AES cipher object in CBC mode with PKCS5 padding
        cipher = AES.new(secret_key, AES.MODE_CBC, iv)

        # Pad the input data to a multiple of AES block size
        padded_data = pad(src.encode('utf-8'), AES.block_size)

        # Encrypt the data
        encrypted = cipher.encrypt(padded_data)

        # Return the encrypted data as a base64-encoded string
        return base64.b64encode(encrypted).decode('utf-8')
    except Exception as e:
        raise RuntimeError("AES encrypt error") from e


def get_headers(access_key: str, secret_key: str) -> dict:
    timestamp = int(round(time.time() * 1000))

    combox_key = access_key + '|padding|' + str(timestamp)
    signature = aes_encrypt(combox_key, secret_key, access_key)

    return {'accessKey': access_key, 'signature': signature}


class MeterSphere:
    def __init__(self, domain: str, access_key: str, secret_key: str):
        self.domain = domain
        self.access_key = access_key
        self.secret_key = secret_key

    def _request(self, path: str, body: dict = None) -> Union[dict, list]:
        """
        :param path:
        :param body: if body is empty, will use get method
        :return:
        """
        url = f"{self.domain.rstrip('/')}/{path.lstrip('/')}"
        print(url)

        headers = {'Content-Type': 'application/json', 'ACCEPT': 'application/json'}
        headers.update(get_headers(self.access_key, self.secret_key))

        if body:
            resp = requests.post(url, headers=headers, json=body)
        else:
            resp = requests.get(url, headers=headers)
        return resp.json()

    def _request_file(self, path: str, file: dict = None, headers: dict = None) -> Union[dict, list]:
        """
        :param path:
        :param file:
        :return:
        """
        url = f"{self.domain.rstrip('/')}/{path.lstrip('/')}"
        print(url)

        headers.update(get_headers(self.access_key, self.secret_key))
        print(headers)

        resp = requests.post(url, headers=headers, data=file)
        return resp.json()

    def get_test_plans_by_project_id(self, project_id: str) -> List[dict]:
        path = '/track/test/plan/list/1/10'
        # projectId 是必须的，其他参数完全没用😂
        body = {
            "projectId": project_id,
        }

        res = self._request(path, body)
        #print(res)

        ret = []
        for r in res.get('data').get('listObject', []):
            ret.append({
                "id": r.get('id'),
                "name": r.get('name'),
                "status": r.get('status'),
            })

        return ret

    def get_test_plan_status(self, name: str, project_id: str) -> str:
        test_plans = self.get_test_plans_by_project_id(project_id)
        test_plan = list(filter(lambda item: item['name'] == name, test_plans))[0]
        return test_plan['status']

    def get_projects(self) -> List[dict]:
        #path = '/project/listAll'
        path = '/project/project/list/all'

        res = self._request(path)

        ret = []
        for r in res.get('data', []):
            ret.append({
                "name": r.get('name'),
                "id": r.get('id'),
            })

        return ret

    def get_envs_by_project_id(self, project_id: str):
        path = f'/api/environment/list/{project_id}'

        res = self._request(path)

        ret = []
        for r in res.get('data', []):
            ret.append({
                "name": r.get('name'),
                "id": r.get('id'),
            })

        return ret

    def run_test_plan(self, project_id: str, test_plan_id: str, env_id: str):
        path = "/track/test/plan/run"

        body = {
            "mode": "serial",
            "reportType": "iddReport",
            # 遇到失败是否直接结束 testplan
            "onSampleError": False,
            "runWithinResourcePool": False,
            "envMap": {
                # project-id: env-id
                project_id: env_id,
            },
            "testPlanId": test_plan_id,
            "projectId": project_id,
            "userId": "admin",
            "triggerMode": "MANUAL",
            "environmentType": "JSON",
            "environmentGroupId": "",
            "requestOriginator": "TEST_PLAN"
        }

        res = self._request(path, body)
        print(res)

        return res

    def get_test_plan_failure(self, test_plan_id: str):
        path = f"/track/test/plan/scenario/case/list/failure/{test_plan_id}"
        res = self._request(path)

        path = f'/track/test/plan/api/case/list/failure/{test_plan_id}'
        res2 = self._request(path)

        ret = []
        for r in res.get('data', []):
            ret.append({
                "name": r.get('name'),
            })

        for r in res2.get('data', []):
            ret.append({
                "name": r.get('name'),
            })

        #ret = res.get('data', [])
        #ret.extend(res2.get('data', []))

        return ret

    def get_share_url(self, report_id: str):
        path = "/track/share/generate/expired"

        body = {
            "customData": report_id,
            "shareType": "PLAN_DB_REPORT",
        }
        res = self._request(path, body)

        return res.get('data').get('id')

    def update_env(self, name: str, project_id: str):
        path = "/setting/environment/update"
        files = MultipartEncoder(
            fields={'request': ('blob', open('blob', 'rb'), 'application/json')}
        )
        headers = {'Content-Type': files.content_type}
        print(type(files))
        res = self._request_file(path, files, headers)
        print(res)

    def update_env_1(self, project_id: str, env: str, env_id: str, doris_package_name: str, host_1, host_2,
                     manager_download, manager_package, doris_download, upgrade_doris_package_name, upgrade_doris_download,
                     upgrade_manager_download, upgrade_manager_package, priority_network):
        path = "/setting/environment/update"
        body = {
            "id": env_id,
            "name": env,
            "projectId": project_id,
            "protocol": None,
            "socket": None,
            "domain": None,
            "port": None,
            "createUser": "admin",
            "createTime": 1721370567113,
            "updateTime": 1722252326779,
            "variables": None,
            "headers": None,
            "config": "{\"commonConfig\":{\"variables\":[{\"name\":\"DorisPackageName\",\"value\":\"" + doris_package_name + "\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":1,\"id\":\"2a4c6ba5-d4fd-860a-e120-9481a1c15efe\"},{\"name\":\"deployIP1\",\"value\":\"" + host_1+ "\",\"type\":\"CONSTANT\",\"files\":[],\"enable\":true,\"quotedData\":\"false\",\"delimiter\":\",\",\"scope\":\"api\",\"num\":3,\"id\":\"c46ea313-888e-2388-cd6e-d6ec4c49749b\"},{\"name\":\"env\",\"value\":\"SelectDB\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":4,\"id\":\"cbdec58f-11af-c89a-eb01-65fe1d0df3f2\"},{\"name\":\"agentPort\",\"value\":\"8991\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":5,\"id\":\"618432f7-2812-ca1b-f914-121547b35f8b\"},{\"name\":\"deployUser\",\"value\":\"root\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":6,\"id\":\"ba8ff269-3ee9-7de3-1d55-eb98b2ed66aa\"},{\"name\":\"deployPassword\",\"value\":\"Cfplhys2022@\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":7,\"id\":\"cf5ee92d-e63b-abc1-cceb-4fea60d4adc9\"},{\"name\":\"managerDownload\",\"value\":\"" + manager_download + "\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":8,\"id\":\"7d6fdd35-32f5-f3ff-56a8-fd9401c50747\"},{\"name\":\"managerPackage\",\"value\":\"" + manager_package + "\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":9,\"id\":\"efb95afb-8de9-d878-b381-72954d2fa8ef\"},{\"name\":\"managerHost\",\"value\":\"" + host_1 + "\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":10,\"id\":\"012500ce-3820-e64e-d405-9a8fc039c586\"},{\"name\":\"managerPort\",\"value\":\"8006\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":11,\"id\":\"70d8e8ed-9ebd-4c69-a2dd-3274a8af6621\"},{\"name\":\"deployPath\",\"value\":\"/root/zm/\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":12,\"id\":\"317d5f3e-e9c3-fa6a-c5cd-6f7701d20913\"},{\"name\":\"deployIP2\",\"value\":\"" + host_2 + "\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":13,\"id\":\"2e2c930a-23fc-bd42-c62b-0eeee707b0f8\"},{\"name\":\"dorisDownload\",\"value\":\"" + doris_download + "\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":14,\"id\":\"9d06ae77-d0fa-91f6-d382-65eb51035728\"},{\"name\":\"priorityNetworks\",\"value\":\"" + priority_network + "\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":15,\"id\":\"95eca3cc-d204-4210-7c1a-a1a58f653b94\"},{\"name\":\"upgradeDorisPackageName\",\"value\":\"" + upgrade_doris_package_name + "\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":16,\"id\":\"675db74b-03e5-9e41-2130-6262765f2a46\"},{\"name\":\"upgradeDorisDownload\",\"value\":\"" + upgrade_doris_download + "\",\"type\":\"CONSTANT\",\"enable\":true,\"scope\":\"api\",\"num\":17,\"id\":\"5dbe7e11-3632-59ee-7242-02a7dfd6cec2\"},{\"name\":\"upgradeManagerDownload\",\"value\":\"" + upgrade_manager_download + "\",\"type\":\"CONSTANT\",\"enable\":true,\"id\":\"0bb38615-9c47-fd71-db7f-121241533fa6\",\"scope\":\"api\",\"num\":18},{\"name\":\"upgradeManagerPackage\",\"value\":\"" + upgrade_manager_package+ "\",\"type\":\"CONSTANT\",\"enable\":true,\"id\":\"98c8afd2-e900-faaf-76d5-eeec8088d9db\",\"scope\":\"api\",\"num\":19},{\"type\":\"CONSTANT\",\"enable\":true,\"id\":\"b28fc4db-87b1-1037-44ef-3c4209aec7d1\",\"scope\":\"api\",\"num\":20}],\"enableHost\":false,\"hosts\":[],\"requestTimeout\":60000,\"responseTimeout\":60000},\"httpConfig\":{\"socket\":\"" + host_1 + ":8006\",\"headers\":[{\"enable\":true}],\"protocol\":\"http\",\"conditions\":[{\"type\":\"NONE\",\"enable\":true,\"id\":\"34aea18d-8b63-4ef1-b191-410b38c161d8\",\"socket\":\"" + host_1 + ":8004\",\"protocol\":\"http\",\"headers\":[{\"enable\":true}],\"domain\":\"" + host_1 + "\",\"time\":1721370581010,\"details\":[{\"name\":\"\",\"value\":\"contains\",\"enable\":true}],\"[object Object]\":1}],\"cookie\":[{\"enable\":false,\"expireTime\":\"1D\"}],\"browser\":\"CHROME\",\"headlessEnabled\":true,\"isMock\":false,\"description\":\"\"},\"databaseConfigs\":[],\"tcpConfig\":{\"classname\":\"TCPClientImpl\",\"reUseConnection\":true,\"nodelay\":false,\"closeConnection\":false},\"sslConfig\":{\"entry\":[],\"files\":[]},\"postStepProcessor\":{\"jsrEnable\":true,\"scriptLanguage\":\"beanshell\"},\"authManager\":{\"hashTree\":[]},\"preProcessor\":{\"jsrEnable\":true,\"scriptLanguage\":\"beanshell\"},\"globalScriptConfig\":{\"filterRequestPreScript\":[],\"connScenarioPostScript\":false,\"connScenarioPreScript\":false,\"filterRequestPostScript\":[],\"isPostScriptExecAfterPrivateScript\":false,\"isPreScriptExecAfterPrivateScript\":false},\"assertions\":{\"duration\":{\"duration\":0},\"jsr223\":[],\"xpathType\":\"xml\",\"regex\":[],\"document\":{\"type\":\"JSON\",\"data\":{\"json\":[],\"xml\":[]},\"enable\":true},\"xpath2\":[],\"jsonPath\":[]},\"postProcessor\":{\"jsrEnable\":true,\"scriptLanguage\":\"beanshell\"},\"preStepProcessor\":{\"jsrEnable\":true,\"scriptLanguage\":\"beanshell\"}}",
            "hosts": None,
            "currentProjectId": project_id,
            "uploadIds": [],
            "variablesFilesIds": []
        }
        data = json.dumps(body)
        with open('file', 'w') as file:
            file.write(data)
        files = MultipartEncoder(
            fields={'request': ('file', open('file', 'rb'), 'application/json')}
        )
        headers = {'Content-Type': files.content_type}
        print(type(files))
        res = self._request_file(path, files, headers)
        print(res)


def main(domain: str, access_key: str, secret_key: str, project_name: str, test_plan_name: str, env_name: str,
         doris_package_name: str, doris_download, upgrade_doris_package_name, upgrade_doris_download, manager_package,
         manager_download, upgrade_manager_package, upgrade_manager_download, host_1, host_2, priority_network):
    m = MeterSphere(domain, access_key, secret_key)

    projects = m.get_projects()
    project_id = list(filter(lambda item: item['name'] == project_name, projects))[0]['id']

    test_plans = m.get_test_plans_by_project_id(project_id)
    test_plan_id = list(filter(lambda item: item['name'] == test_plan_name, test_plans))[0]['id']
    print(test_plan_id)

    envs = m.get_envs_by_project_id(project_id)
    env_id = list(filter(lambda item: item['name'] == env_name, envs))[0]['id']
    print(env_id)

    m.update_env_1(project_id, env_name, env_id, doris_package_name, host_1, host_2, manager_download, manager_package, doris_download,
    upgrade_doris_package_name, upgrade_doris_download, upgrade_manager_download, upgrade_manager_package, priority_network)

    print(f'running test plan {project_name} {test_plan_name} {env_name}')
    test_id = m.run_test_plan(project_id, test_plan_id, env_id).get('data')

    share_url_id = m.get_share_url(test_id)

    # wait testplan end
    while True:
        status = m.get_test_plan_status(test_plan_name, project_id)
        if status != 'Underway' or status == 'Completed':
            break
        print('waiting for test plan end')
        time.sleep(3)

    res = m.get_test_plan_failure(test_plan_id)
    report_share_url = f'{domain.rstrip("/")}/track/share-plan-report?shareId={share_url_id}'
    if len(res) > 0:
        # if test plan failed, print test plan report link and errors
        print(f'check errors {len(res)} -> ${report_share_url}')
        print(json.dumps(res))
        send_msg("manager 回归测试", "Failed", report_share_url, res)
        exit(1)
    send_msg("manager 回归测试", "Success", report_share_url, res)


def send_msg(job_name, job_status, report_url, failCase):
    # get send_flag and feishu_webhook url
    feishu_webhook = "https://open.feishu.cn/open-apis/bot/v2/hook/c5f953fc-efb2-41ea-8049-8ed1fc3d7121"

    msg_dict = dict()
    msg_dict['msg_type'] = 'post'
    fail_case_list = []
    if len(failCase) > 0:
        for failCase in failCase:
            fail_case_list.append(failCase.get("name"))
        result = "failed case is: \n" + '\n'.join(fail_case_list)
    else:
        result = ""
    msg_dict['content'] ={
        "post": {
            "zh_cn": {
                "title": job_name,
                "content": [
                    [{
                        "tag": "text",
                        "text": "result: "
                    }, {
                        "tag": "a",
                        "text": job_status + "\n",
                        "href": report_url
                    }, {
                        "tag": "text",
                        "text": result
                    }]
                ]
            }
        }
    }

    msg_j = json.dumps(msg_dict)
    res = requests.post(feishu_webhook, data=msg_j, headers={'Content-Type': 'application/json'})
    print('send message to Feishu , res is :', res.text)


if __name__ == '__main__':
    """
    触发 meterSphere 的测试计划，并返回测试计划执行结果
    """
    # meterspere apikey
    #api_key = 'pemqOEaJmIcCm3PG'
    api_key = sys.argv[1]
    # meterspere api-secret
    #api_secret = 'b4tDSLY7qlpylEu8'
    api_secret = sys.argv[2]
    # metersphere endpoint
    #endpoint = 'http://172.20.48.145:8081/'
    endpoint = sys.argv[3]
    project_name = sys.argv[4]
    test_plan_name = sys.argv[5]
    env_name = sys.argv[6]
    doris_package_name = sys.argv[7]
    doris_download = sys.argv[8]
    upgrade_doris_package_name = sys.argv[9]
    upgrade_doris_download = sys.argv[10]
    manager_package = sys.argv[11]
    manager_download = sys.argv[12]
    upgrade_manager_package = sys.argv[13]
    upgrade_manager_download = sys.argv[14]
    host_1 = sys.argv[15]
    host_2 = sys.argv[16]
    priority_network = sys.argv[17]

    main(endpoint, api_key, api_secret, project_name, test_plan_name, env_name, doris_package_name, doris_download,
         upgrade_doris_package_name, upgrade_doris_download, manager_package, manager_download, upgrade_manager_package,
         upgrade_manager_download, host_1, host_2, priority_network)



