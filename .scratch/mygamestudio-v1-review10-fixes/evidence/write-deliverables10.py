from pathlib import Path
import json,subprocess
W=Path('/tmp/mgs-review10-j5225ubn');S=Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
read=lambda p:json.loads((W/p).read_text())
def rows(p):
 d=read(p);return d['rows'] if isinstance(d,dict) and 'rows' in d else d
original_files=['spec-probes.json','spec-independent-probes.json','spec-extra-pending.json','curl-new-probes.json','curl-extra-probes-5.json','path-extra-probes-5.json','path-boundaries-6.json','curl-boundaries-6.json','curl-adversarial-7.json','new-probes-8.json','new-probes-9.json','parallel-curl-supplement.json']
original=[]
for name in original_files:
 for r in rows(name):
  out={k:r[k] for k in ['id','expected','expected_anchor','actual_anchor','anchor','current','before_batch','observed_bug','posts','post_count','first_has_warning','disclosed_corrupt','second_body_exists','a_comment_count','b_comment_count'] if k in r}
  out['source']=name;out['observed_bug']=r.get('observed_bug')
  out['observed_bug_field_present']='observed_bug' in r
  if r.get('id')=='full-diagnostic-body':out['classification']='accepted SP-25 residual; raw expected and observed_bug preserved'
  elif r.get('id')=='retry-closed-control':out['classification']='accepted conservative flip';out['contract_expected']='MISSING'
  elif r.get('id')=='true-url-flag':out['classification']='accepted --url parsing limit'
  else:out['classification']='historical replay'
  original.append(out)
new=read('main-confirm/new-curl-probes.json')
sp30=[r for r in new['rows'] if r['observed_bug']]
finding={'id':'SP-30','axis':'Spec','priority':'P2','title':'上传文件参数 glob 绕过单请求约束，首次 PUT 成功后仍判直连被拒','file':str(S/'acceptance/18-complete-package-acceptance/run.sh'),'lines':[258,264,314,315,338,344],'introduced_by_batch':False,'also_reproduced_on':['e3741c6','3f3031a'],'expected':'MISSING','actual':'OK','cases':[r['id'] for r in sp30],'evidence':'main-confirm/new-curl-probes.json','guard':'spec/upload_glob_guard.diff','causal_matrix':'spec/upload-causal-matrix.json','contract_sources':[str(S/'.scratch/mygamestudio-v1-review7-fixes/issues/01-curl-anchor-connection-proof-completion.md')+':16',str(S/'.scratch/mygamestudio-v1-review6-fixes/issues/02-curl-anchor-connection-params-and-single-url.md')+':14']}
summary={
 'review':10,'source_root':str(S),'workspace':str(W),'baseline':'e3741c6','product_target':'66b8506','actual_head':read('start.json')['head'],
 'batch_commits':['0029067','fe8572d','66b8506'],'batch_commit_count':3,'extra_head_commit':'2288aeb (handoff document only)',
 'verdict':{'SP-27':'fixed','SP-28':'fixed with disclosed retry control rejection','SP-29':'specified URL-glob cases fixed','new_finding_count':1,'new_regressions_found':0,'v1_technical_closeout':False,'v1_closeout':False,'reason':'SP-30 remains reproducible; validation exceptions are separately disclosed'},
 'axes':{'Standards':{'hard_violations':0,'reportable_smells':0,'findings':0,'worst_priority':None,'report':'standards/standards-review.md'},'Spec':{'findings':1,'worst_priority':'P2','ids':['SP-30'],'report':'spec/spec-review.md'}},
 'original_probes':original,'new_findings':[finding],
 'new_probe_rows':[{k:r[k] for k in ['id','group','expected','exit','observed_bug','server_hits','current','e3741c6','3f3031a','upload_guard','upload_glob_guard','restored']} for r in new['rows']],
 'independent_confirmation':read('main-confirm/confirmation.json'),
 'arity_audit':{'total':67,'mismatches':0,'table_counts':{'CURL_VALUE_SHORT':19,'CURL_PLAIN_SHORT':15,'CURL_VALUE_LONG':19,'CURL_PLAIN_LONG':14},'scope':'local curl 8.7.1 help, no-argument behavior, manual and connection-semantics annotations; not proof of complete curl safety','evidence':'spec/arity-audit.json'},
 'mutations':read('mutation-results-10.json'),'baseline_red_count_explanation':{'core_counterexamples':8,'disclosed_retry_control':1,'all_current_assertions':9,'single_direction_counts':[5,2,2]},
 'historical_execution':read('history-execution-10.json'),'retained':read('acceptance-probes-6.json'),
 'suites':read('suite-results-10.json'),'driver':{**read('driver-result-10.json'),'pass':33,'fail':0,'adaptation_diff':'driver-isolation-10.diff'},
 'syntax_checks':read('syntax-checks-10.json'),'evidence_audit':read('verified-results-10.json'),
 'validation_limits':[
  {'id':'package-three-secret-tests-not-run','severity':'coverage limitation','tests':read('suite-results-10.json')[0]['skipped'],'reason':'Tests intentionally persist plaintext synthetic tokens, contrary to this review hard boundary. They were not executed; package suite is partial, not a full suite PASS.'},
  {'id':'original-probe-nonloopback-address-interpretation','severity':'execution-boundary limitation','case':'terminator-attached-option','evidence':'new-probes-9.json','observation':'Original command contains -- -sSm2 before the explicit loopback URL. curl treated the first token as a URL-like input and timed out for 2 seconds. No packet capture or egress fence was present.','conclusion':'Cannot prove all DNS/connection attempts in the entire review stayed on loopback; do not label the complete execution strictly loopback-isolated. No real GitHub request or successful nonloopback request is evidenced.'},
  {'id':'accepted-residuals','items':['SP-25 exact diagnostic line in response body','--url parsing','three or more shell layers','conservative multi-URL rejection','no-cache posts=2','concurrent interleaving','migration-truncated current receipt','ambient remapping that still names .1']},
  {'id':'synthetic-events','reason':'Real local curl command, exit, stdout and stderr are wrapped into commandExecution events; no product or acceptance model turn was run.'}
 ],
 'source_boundary':read('final-boundary-check-10.json'),'cleanup':read('cleanup-10.json'),'secret_scan':read('token-output-scan-10.json'),
 'report':'review-10.md'
}
(W/'verification-summary-10.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
intro='''# MyGameStudio v1 第十轮独立复审

**交付判定：SP-27～29 的指定反例均真实修复；发现 SP-30 一项 P2 历史遗漏，未发现本批引入的新回归；目前不具备 v1 技术收口条件。**

Standards 为 0 硬违规 / 0 报告级异味；Spec 为 1 项 P2。另有两个验证限制必须保留：package 的三个主动令牌落盘测试未运行；原探针一行含非 loopback 字面地址的解析路径，无法证明整轮网络严格限于 loopback。不得把本报告缩写为“五套件完整全绿、所有边界无例外通过”。

## 固定版本与实际范围

- 真实仓库 `/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`，main；开始和结束 HEAD 均为 `2288aeb86fac18c7d69e7a2ca291bbb6e50a32c5`，工作树干净，全部受控文件字节未变。
- 产品目标 `66b8506`；额外 `2288aeb` 只有第十轮交接文档。实际批次命令为 `git diff e3741c6..66b8506`，实数恰三提交：`0029067`、`fe8572d`、`66b8506`。
- 唯一产品提交为 `66b8506`：run.sh 的一个函数、测试及刷新证据；plugin/、dist/ 无差异。交付包 SHA-256 仍为 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`。
- 所有副本、变异、临时安装、探针及本报告均在本任务 `/tmp/mgs-review10-j5225ubn`。评审按行为与提交内容判断，不以实施工具作依据。

## 新增发现

### SP-30 · P2 · 上传文件名 glob 绕过单请求约束

`acceptance/18-complete-package-acceptance/run.sh:258/264` 接纳 `T/--upload-file`；`:314–316` 与 `:335–339` 直接消费其值；`:309/:344` 的 glob 检查只覆盖 URL 位置参数。因而上传文件参数可展开多个请求，即使 URL 只有一个且不含 `{}` 或 `[]`。

真实反例形态：

```sh
/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS \\
  -T '{a.txt,b.txt}' http://127.0.0.1:动态端口/upload/
```

本任务服务器接收首个 `PUT /upload/a.txt` 的 18 字节，关闭监听并返回 HTTP 200 与 `UPLOAD_SUCCESS`；第二次连接产生真实 stderr `curl: (7) Failed to connect to 127.0.0.1 …`，进程 exit 7。当前判据仍 **OK**，应为 **MISSING**。这是已有成功请求后错误认定“直连被拒”，不是响应正文模拟诊断行的 SP-25 例外。

违反 [review7 票 01 第 16 行](SOURCE/.scratch/mygamestudio-v1-review7-fixes/issues/01-curl-anchor-connection-proof-completion.md:16)“失败证据须能证明对替身的连接未被允许”，并落入 [review6 票 02 第 14 行](SOURCE/.scratch/mygamestudio-v1-review6-fixes/issues/02-curl-anchor-connection-params-and-single-url.md:14) 的失败归属合同。本机 curl 8.7.1 手册明确支持上传文件参数 glob。

六种真实形态全部复现：短分离 `-T value`、长分离 `--upload-file value`、短粘连 `-Tvalue`、聚合 `-sSTvalue`、`item[1-2].txt`、URL 在 `--` 后。六例在 `e3741c6` 与 `3f3031a` 也均 OK，故为**历史遗漏，不是 66b8506 引入**。

只在提取函数中对上传值增加 glob 拒绝：六例 OK→MISSING→OK；短/长普通单文件上传失败对照全程 OK。较宽的“移除所有上传旗标”守卫另有留档，它会误伤这两个对照，不能混同精确守卫。未修改产品、未提交修复。

独立 Spec 轴实跑后，主审在另一个目录只改探针 W 再次真实执行 36 例，结果逐项一致。[主审真实证据](main-confirm/new-curl-probes.json)、[一致性核验](main-confirm/confirmation.json)、[精确守卫](spec/upload_glob_guard.diff)、[因果矩阵](spec/upload-causal-matrix.json)。

## SP-27～29 逐项复核

g/J/Z 正确归入无值表；`--retry` 从接纳表移除；URL 位置参数和 `--` 后参数中的 `{}`/`[]` 均拒绝。四表共 67 项逐一对读本机帮助、无参执行和手册，元数错分类为 0；该结论不等于连接语义完备，SP-30 正是其中遗漏。

下表“原 bug”原样保留历史脚本的 `observed_bug`，不靠改写旧判据抹去例外。

| 原探针 | 本轮合同期望 | 当前 | 原 bug | 说明 |
|---|---|---|---|---|
'''.replace('SOURCE',str(S))
table=[]
for r in rows('new-probes-9.json')+rows('parallel-curl-supplement.json'):
 note='符合'
 expected=r['expected']
 if r['id']=='full-diagnostic-body':expected='OK';note='SP-25 已接受残余；原期望 MISSING'
 if r['id']=='retry-closed-control':expected='MISSING';note='已披露翻转；原脚本期望 OK'
 table.append(f"| {r['id']} | {expected} | {r['current']['anchor']} | {str(r['observed_bug']).lower()} | {note} |")
(W/'review-10.md').write_text(intro+'\n'.join(table)+'\n')
print(json.dumps({'summary_written':True,'report_part':1,'original_probe_rows':len(original),'new_findings':len(summary['new_findings'])}))
