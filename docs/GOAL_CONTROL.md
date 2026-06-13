# Goal Control Template

Updated: 2026-05-28

이 문서는 앞으로 사용자가 짧은 `goal` 명령을 보낼 때 적용할 고정 지시문
양식이다. 매번 긴 지시문을 반복하지 않고, 사용자는 `목표`와 `예시`만
전달한다.

## How To Invoke

사용자는 앞으로 아래 형식으로 지시한다.

```text
goal

docs/GOAL_CONTROL.md 기준으로 실행해주세요.

목표:
[이번 작업 목표]

예시:
[원하는 산출물, 작업 방향, 우선순위, 주의사항]
```

예:

```text
goal

docs/GOAL_CONTROL.md 기준으로 실행해주세요.

목표:
Replay Validation Foundation의 cost-source blocker를 다음 deterministic
state까지 닫아주세요.

예시:
approved-cost-profile import/validation skeleton을 만들고, source reference
없는 값은 거부하며, 검증 후 NEXT_TASK에 다음 exact command를 남겨주세요.
```

## Fixed Instruction Template

아래 작업을 deterministic orchestration 원칙에 따라 진행한다.

LLM은 작업 전체를 임의로 결정하지 않는다. 문서화된 상태 머신, DAG,
단계별 gate, artifact contract, validation rule 안에서만 판단, 분류,
요약 역할을 수행한다.

## Orchestration Principles

1. 플로우차트는 폐기하지 않는다.
2. 작업 흐름은 상태 머신, DAG, 단계별 gate, validation loop로 관리한다.
3. LLM은 알고리즘을 대체하지 않는다. LLM은 context 해석, 분류, 요약,
   anomaly explanation, hypothesis generation에만 사용한다.
4. task routing, retry, blocker classification, validation, promotion gate는
   deterministic rule로 처리한다.
5. 모든 단계는 재시작 가능해야 하며, 현재 상태와 다음 exact command를
   문서에 남긴다.
6. 한 블록이 끝나도 다음 deterministic state가 있으면 이어서 진행한다.
7. 서로 같은 artifact를 읽고 쓰는 command는 병렬 실행하지 않는다. 특히
   `post_eligible_paper_recheck_runner`, `paper_observation_refresh_runner`,
   `paper_evidence_operator_summary`, source/outcome ledger audit 계열은
   같은 `backtest/results` 상태를 갱신하므로 항상 순차 실행한다.

## Resume Procedure

작업 시작 또는 재개 시 아래 문서를 먼저 읽고 현재 위치를 복원한다.

- `docs/GOAL_CONTROL.md`
- `docs/README.md`
- `docs/NEXT_TASK.md`
- `docs/CURRENT_PROBLEM_STATUS.md`
- `docs/ROADMAP.md`
- `docs/STRATEGY_DESIGN_MATRIX.md`
- `docs/DATA_STORAGE_CONTRACT.md`
- 필요한 관련 active contract/strategy/validation 문서

Archived prompt, legacy idea, retired plan, and old review documents under
`docs/archive/` are historical references only. They are not current work
instructions unless a top-level active document explicitly promotes them back.

복원 후 사용자가 보낸 `목표`와 `예시`를 이 문서의 고정 양식에 적용한다.

## Goal Injection

사용자가 보낸 목표는 아래 위치에 삽입해서 해석한다.

```text
목표:
[USER_GOAL]

예시:
[USER_EXAMPLE]
```

사용자가 목표만 보내고 예시를 생략하면, `docs/NEXT_TASK.md`의
`Current next command` 또는 `Next exact command`를 기본 예시로 사용한다.

사용자가 `goal`만 보내면, 아래 순서로 진행한다.

1. `docs/GOAL_CONTROL.md` 복원
2. `docs/NEXT_TASK.md`에서 next exact command 확인
3. `docs/CURRENT_PROBLEM_STATUS.md`에서 blocker 상태 확인
4. 가장 우선순위가 높은 deterministic next command부터 실행

## Scope

각 작업은 기본적으로 아래 범위를 따른다.

1. 현재 문서, 코드, artifact 상태 복원
2. 현재 blocker와 next exact command 확인
3. 필요한 builder, validator, report, operator path 구현 또는 보강
4. artifact 생성 또는 재생성
5. direct tests 실행
6. full validation 실행
7. 문서 업데이트
8. 중립 재검토 및 방향성 확인(미래를 생각해서)
9. 문제점 발견 시 수정 후 재검증
10. 다음 deterministic state 또는 next exact command로 이동

## Code Growth / Decomposition Principles

앞으로 모든 패치는 기능 추가보다 코드 구조 보존을 우선한다. 새 artifact,
validator, dashboard panel, collector helper, operator report를 추가할 때는
아래 원칙을 상위 원칙으로 적용한다.

1. 기존 파일이 비대해지는 방향의 패치는 기본적으로 금지한다.
2. 한 파일에 새 책임을 계속 누적하지 않는다. 새 책임은 독립 builder,
   validator, closeout, panel, helper 모듈로 분리한다.
3. behavior-preserving extraction을 우선한다. 기능 변경과 구조 분리를 같은
   batch에서 섞지 않는다.
4. 이미 큰 파일에 코드를 추가해야 하는 경우, 먼저 해당 파일의 책임 지도와
   safe extraction plan을 만든다.
5. 패치 단위는 “하나의 책임, 하나의 artifact contract, 하나의 검증 루프”를
   기본 단위로 한다.
6. 공통 로직은 2회 이상 반복될 때 helper로 분리하되, premature abstraction은
   피한다.
7. GUI 패치는 한 panel 또는 한 model section 단위로 제한하고, 타입, sync audit,
   screenshot check를 함께 갱신한다.
8. collector/miniPC/systemd/Telegram 패치는 collector-only, read-only report,
   notification, deployment 영역을 서로 섞지 않는다.
9. strategy/replay/cost/source artifact는 실행 경로와 절대 결합하지 않는다.
10. 새 코드가 기존보다 이해하기 어렵거나 테스트 없이 책임을 확장한다면
    작업을 멈추고 decomposition preparation artifact를 먼저 만든다.

## Over-Engineering Control Principles

이 프로젝트는 research-only/no-execution 안전장치가 많기 때문에, 검증
계층이 늘어나는 것 자체는 필요할 수 있다. 그러나 artifact, gate, 문서,
dashboard panel이 계속 증가하면 운영자가 현재 상태를 이해하지 못하는
위험이 커진다. 앞으로 모든 goal 작업은 아래 오버엔지니어링 통제 원칙을
함께 적용한다.

1. 새 artifact를 만들기 전에 기존 artifact로 같은 질문에 답할 수 있는지
   먼저 확인한다.
2. 새 artifact의 목적은 아래 중 하나여야 한다.
   - 기존 blocker를 더 정확히 분류
   - operator 혼동을 줄임
   - no-execution/replay-safe 경계를 더 명확히 함
   - 미래 작업의 명확한 stop/resume 조건을 만듦
3. 단순 상태 요약만 추가하는 artifact는 기본적으로 만들지 않는다. 기존
   master board, closeout, dashboard panel에 넣을 수 있으면 그쪽을 우선한다.
4. 비슷한 artifact가 3개 이상 생기면 다음 기능 추가 전에 master index,
   rollup, or closeout으로 묶는 작업을 검토한다.
5. gate를 추가할 때는 “무엇을 허용하는지”보다 “무엇을 계속 금지하는지”를
   명확히 기록한다.
6. 새 blocker 이름을 만들 때는 기존 blocker taxonomy와 중복되지 않는지
   확인한다. 같은 의미의 BLOCKED/DATA_SOAK/PARK/DESIGN_REVIEW를 새 이름으로
   반복하지 않는다.
7. 새 문서는 active instruction인지, historical note인지, archive 후보인지
   명확히 표시한다.
8. 새 GUI panel은 operator decision을 실제로 줄이지 못하면 추가하지 않는다.
   표시만 늘리는 패치는 피한다.
9. 새 Telegram 메시지는 사용자가 즉시 취할 수 있는 행동 또는 wait reason을
   더 명확히 할 때만 추가한다.
10. “언젠가 필요할 수 있음”만으로 runtime, collector, strategy, GUI, docs를
    동시에 수정하지 않는다. 먼저 read-only feasibility/contract로 닫는다.
11. 모든 새 모듈은 다음 중 하나의 종료 조건을 가져야 한다.
    - READY_WITH_BLOCKERS로 멈춤
    - WAIT_FOR_DATA로 멈춤
    - DESIGN_REVIEW로 멈춤
    - ARCHIVE/SUMMARY 후보로 멈춤
    - 다음 exact command를 하나만 남기고 멈춤
12. 장기적으로 필요하지만 지금 실행하지 않을 기능은 implementation이 아니라
    contract, feasibility, or preparation artifact로만 둔다.

## Strategy Evidence Loop Priority

2026-06-05 이후 전략 관련 goal은 “안전장치 추가”보다 “현재 안전장치 안에서
paper/shadow 관찰 근거를 실제로 늘리는 것”을 우선한다. 이 프로젝트의 현재
핵심 병목은 전략 아이디어 부족이 아니라, 전략 판단을 돈이 들어가지 않는
관찰 루프에서 반복 검증하고 신뢰도를 업데이트하는 과정이다.

2026-06-07 방향성 고정:

사용자의 active strategy direction은 “완벽한 데이터가 모일 때까지 대기”가
아니다. 앞으로 전략 작업은 낮은 신뢰도에서 시작하되 돈이 나가지 않는
paper/shadow-style 관찰 row를 반복적으로 쌓고, source/outcome 연결이 늘어날수록
신뢰도를 갱신하는 방향으로 진행한다.

따라서 전략 관련 goal의 우선순위 판단 질문은 항상 아래 순서로 한다.

1. 이 작업이 실제 paper/shadow 관찰 row를 늘리는가?
2. 이 작업이 source row, outcome row, complete evidence chain을 늘리는가?
3. 이 작업이 confidence rollup을 실제 최신 evidence에 맞게 갱신하는가?
4. 이 작업이 operator가 다음 행동을 더 명확히 결정하게 하는가?
5. 위 네 가지에 해당하지 않고 정의, closeout, GUI, 문서만 늘리는가?

5번에 해당하면 기본적으로 후순위로 둔다. 단, 기존 동기화 오류, 권한 누수,
known-at 오염, stale artifact 표시처럼 관찰 루프의 신뢰성을 직접 해치는 문제는
즉시 고친다.

### Strategy Evidence Hard Priority Gate

전략/검증 관련 작업을 시작하기 전에는 반드시 아래 순서로 작업 가치를
판단한다. 이 gate는 “대기만 하는 상태”로 후퇴하거나, 같은 blocker를 설명하는
artifact만 늘리는 것을 막기 위한 강제 기준이다.

1. 실제 append-only paper/shadow-style 관찰 row를 늘릴 수 있으면 그 작업을
   우선한다.
2. 이미 존재하는 paper row에 source row, outcome row, complete evidence chain을
   붙일 수 있으면 그 작업을 최우선한다.
3. source/outcome 연결이 막혔을 때는 새 설명 artifact를 만들기보다 기존 writer,
   materializer, preflight, ledger audit 경로로 실제 row 증가 가능성을 먼저
   확인한다.
4. confidence는 수익률/edge가 아니라 row quality, source coverage, outcome
   coverage, known-at completeness, decision diversity, blocker 감소로만 갱신한다.
5. 새 closeout, GUI, 문서, definition artifact는 위 1-4번을 직접 진전시키거나
   stale/mismatch/permission 문제를 막는 경우에만 우선한다.
6. “완벽한 데이터가 없으니 기다림”은 기본 결론이 아니다. 먼저 저신뢰 관찰 row
   또는 기존 row의 source/outcome linkage를 늘릴 수 있는지 확인한다.
7. 그래도 row/linkage를 늘릴 수 없으면, 다음 exact command와 재확인 trigger를
   하나만 남기고 멈춘다.

앞으로 전략/검증 패치는 아래 우선순위를 따른다.

1. 새 전략 추가보다 LEFU/LVOR/MQRF의 paper observation row, source row,
   base outcome row, confidence evidence chain을 늘린다.
2. 새 gate/artifact를 만들기 전에 기존 paper evidence loop에서 실제 관찰
   row를 더 쌓을 수 있는지 확인한다.
3. 과거 데이터는 버리지 않는다. historical tier, decay, comparability,
   provenance를 적용해 preliminary evidence로 쓰되, forward/paper evidence와
   구분해서 기록한다.
4. confidence 상승은 수익률/edge 주장으로 처리하지 않는다. 처음에는
   observation quality, known-at completeness, decision diversity, source
   coverage, outcome coverage, blocker 감소로만 본다.
5. 저신뢰 shadow로 바로 권한을 여는 것이 아니라, low-confidence paper
   observation → source/outcome append → confidence rollup → manual shadow
   review 순서를 따른다.
6. 다만 전략 발전을 막는 수준의 과도한 closeout/artifact 확장은 중단한다.
   새 artifact가 실제 paper row 누적, source/outcome 연결, shadow review
   준비에 직접 기여하지 않으면 만들지 않는다.
7. GUI/문서 작업은 현재 상태를 이해하기 쉽게 만드는 범위로 제한한다. 전략
   판단 루프 자체를 진전시키지 못하는 표시 개선은 후순위로 둔다.
8. 매 batch 완료 시 “이번 작업이 실제 관찰 근거를 늘렸는가, 아니면 안전
   경계만 늘렸는가”를 완료 보고에 명시한다.
9. shadow/live/scanner/executor/promotion 권한은 계속 deterministic gate와
   manual review 없이 열 수 없다.
10. “저신뢰 shadow 실행”이라는 표현은 실제 거래소 shadow/executor 연결을 뜻하지
    않는다. 현재 active meaning은 low-confidence paper/shadow observation ledger에
    append-only row를 남기는 것이다.
11. runtime shadow enablement, scanner/executor 연결, live/promotion은 별도 manual
    enablement design과 service/runtime gate가 통과하기 전까지 계속 닫는다.
12. 새 guard를 만들 때는 관찰 루프 진행을 막는 stale/mismatch/permission 문제를
    해결하는 경우에만 우선한다. “나중에 필요할 수 있음”만으로 새 gate를 늘리지
    않는다.

### Strategy Work Stop/Resume Rule

전략 작업이 다음 중 하나에 해당하면 새 정의 작업을 멈추고 관찰 루프 쪽으로
돌아간다.

- paper row 수가 전략별 최소 검토 기준보다 낮은데 새 정의 artifact만 늘어나는
  경우
- source/outcome 연결 row가 부족한데 GUI/문서/closeout만 늘어나는 경우
- 같은 blocker를 다른 이름으로 다시 설명하는 경우
- 사용자가 “그래서 언제 shadow/검증이 되느냐”라고 물을 만큼 실행 가능한
  다음 단계가 불명확해진 경우

이때 기본 next command는 아래 계열을 우선한다.

```bash
python3 -m backtest.research.post_eligible_paper_recheck_runner
python3 -m backtest.research.paper_observation_refresh_runner
python3 tools/validate_current_state.py
```

위 command는 한 shell에서 순서대로 실행해야 한다. 병렬 실행하면 중간
artifact가 서로 다른 생성 시점을 참조해 operator summary가 일시적으로
낡은 source ledger 상태를 표시할 수 있다.

## Dashboard Sync Principles

GUI는 operator가 현재 상태를 잘못 이해하지 않도록 자동 동기화와 재시작
필요성을 명확히 구분해야 한다.

1. 브라우저 프론트엔드는 `/api/overview`를 주기적으로 `cache: no-store`로
   다시 읽어야 한다.
2. dashboard API는 mutation endpoint를 만들지 않는다. 원격 miniPC artifact
   동기화는 read-only rsync/import만 허용한다.
3. dashboard API 요청 시 가능한 경우 miniPC result artifact를 best-effort로
   sync하되, collection 실행, source policy 변경, main PC direct collection은
   금지한다.
4. Python dashboard model 코드가 바뀐 경우에는 서버 프로세스 재시작이 필요할
   수 있다. 이 경우 GUI와 docs에 “restart required” 또는 “server reload
   required”를 명시한다.
5. frontend TSX/CSS가 바뀐 경우에는 `npm run build` 후 서비스가 새 dist를
   서빙해야 한다. 단순 artifact 값 변경과 프론트엔드 빌드 변경을 혼동하지
   않는다.
6. 새 GUI 숫자/문구는 canonical artifact에서만 읽고, 별도 계산을 반복하지
   않는다.
7. GUI, Telegram, docs가 같은 지표를 서로 다르게 표시한 이력이 있으면, 다음
   GUI 작업은 기능 추가가 아니라 sync audit/test 강화가 우선이다.
8. GUI 자동 동기화는 “최신 artifact 표시”를 뜻한다. artifact 자체를 새로
   생성하거나 collector를 실행하는 자동화로 확장하지 않는다.

### Complexity Budget Check

아래 조건 중 하나라도 해당하면 다음 작업은 기능 추가보다 정리/통합/표시
개선 쪽을 우선 검토한다.

- 같은 주제의 latest artifact가 5개 이상 존재하는 경우
- operator가 현재 상태를 이해하려면 3개 이상의 문서를 함께 읽어야 하는 경우
- GUI, Telegram, docs, artifact가 같은 숫자를 서로 다르게 표현한 이력이 있는
  경우
- 새 artifact가 Stage 4, replay, shadow, live, promotion이라는 단어를 포함하지만
  실제 permission을 열지 않는 경우
- 새 builder가 다른 builder 3개 이상을 단순 재포장하는 경우
- tests가 늘었지만 실패 시 operator가 무엇을 해야 하는지 artifact에 남지 않는
  경우

이 경우 기본 대응은 다음 순서다.

1. 기존 artifact inventory 확인
2. 중복 blocker/status 이름 정리
3. master rollup 또는 closeout으로 묶기
4. GUI/Telegram 문구가 같은 의미를 쓰는지 확인
5. 새 기능 구현은 그 다음 batch로 미룬다

### File Health Guard

다음 조건 중 하나라도 해당하면 새 기능 추가보다 분리/정리 작업을 우선한다.

- 단일 Python 파일이 약 800줄을 넘고 새 책임을 추가해야 하는 경우
- 단일 TSX/CSS 파일이 약 500줄을 넘고 새 UI 책임을 추가해야 하는 경우
- 함수 하나가 여러 artifact를 읽고, 상태 판단과 렌더링/출력을 동시에 하는 경우
- 같은 status/blocker/visibility 변환 로직이 여러 파일에 반복되는 경우
- 테스트가 문자열 snapshot만 있고 구조적 contract test가 없는 경우
- 새 artifact가 GUI, Telegram, docs, validator 중 2개 이상에 동시에 표시되는 경우

이 경우 기본 순서는 다음이다.

1. characterization test 추가
2. 현재 출력/JSON contract 고정
3. pure helper 또는 builder로 분리
4. 기존 call site를 helper 호출로 교체
5. focused test, full direct tests, relevant validation 실행
6. 기능 변경은 별도 batch에서 진행

## LLM Role Boundary

LLM은 다음만 수행할 수 있다.

- 문서, 로그, artifact 해석
- blocker 분류
- operator 설명문 생성
- 이벤트, 감성, 상황 요약
- hypothesis 생성
- post-review 또는 anomaly explanation

LLM은 다음을 수행하면 안 된다.

- 진입/청산 결정
- 포지션 사이징
- 전략 promotion 승인
- live/shadow 연결 승인
- 비용/수익 값을 임의 생성
- threshold mining
- secrets/API key 접근
- 실거래 설정 변경

## Deterministic Rails

아래는 deterministic rule로 처리한다.

- 상태 전이
- retry 정책
- validation 통과/실패 판정
- artifact contract validation
- blocker priority
- cost/source readiness 판정
- replay eligibility gate
- operator visibility
- promotion/shadow/live hard stop

## Project-Specific Operating Principles

이 프로젝트의 이전 작업 이력을 기준으로, 아래 원칙을 모든 goal 작업에
추가 적용한다.

1. 데이터 수집 범위와 전략 검증 집중 범위를 혼동하지 않는다. 수집은 넓게
   유지하고, 판단/검증 우선순위만 좁힌다.
2. miniPC collector state, main workspace import state, GUI display state를
   분리해서 판단한다. 셋 중 하나의 지연을 수집 실패로 단정하지 않는다.
3. GUI/Telegram 문구는 operator가 “왜 아직 거래하지 않는지”를 이해하게
   만들어야 한다. READY, BLOCKED, PARK, DATA_SOAK, DESIGN_REVIEW는 같은
   의미로 쓰지 않는다.
4. dashboard 숫자는 source artifact와 sync audit으로 검증한다. 표시를 맞추기
   위해 source policy, replay gate, readiness flag를 완화하지 않는다.
5. raw rows, imported parquet, maturity schedule, replay-safe feature는 서로
   다른 단계다. raw 수집 성공을 replay/cost-fill readiness로 승격하지 않는다.
6. historical backfill, synthetic timestamp, review-only LLM suggestion은
   replay-safe evidence로 취급하지 않는다.
7. 유료 API나 새 데이터 소스는 무료/개인급 수집 품질의 병목이 명확히
   분류된 뒤 효용 audit을 거쳐 검토한다.
8. 문서 정리는 삭제보다 inventory, summary, archive plan, closeout 순서로
   진행한다.
9. “작은 선택 작업”도 운영 혼동을 줄이거나 future blocker를 명확히 닫는
   경우에만 수행한다.
10. 장시간 자동 루프는 새 artifact를 계속 늘리는 것이 목적이 아니다. 다음
    trigger가 없으면 wait-state를 명확히 하고 중단한다.

## Work Loop

각 블록마다 다음 루프를 반복한다.

1. 현재 상태 복원
2. next exact command 확인
3. deterministic rule에 따라 작업 범위 확정
4. 필요한 코드, 문서, artifact 수정
5. artifact 재생성
6. direct tests 실행
7. full validation 실행
8. 문서에 완료 내용, 검증 결과, 남은 blocker, 다음 exact command 기록
9. 중립 재검토
10. 수정사항이 있으면 수정 후 다시 검증
11. 다음 exact command가 있으면 계속 진행

## Token / Instruction Budget Control

앞으로 goal 지시문과 완료 보고는 안전 경계를 유지하되 불필요한 반복을 줄인다.
이 문서에 이미 고정된 금지사항, 검증 원칙, no-execution 경계는 매 goal마다
전부 다시 나열하지 않는다.

1. 사용자의 goal 지시문은 기본적으로 짧게 작성한다.
   - 목표
   - 생성/수정 대상
   - 이번 작업에서 특별히 중요한 금지 1-3개
   - 검증
   위 네 항목이면 충분하다.
2. `docs/GOAL_CONTROL.md 기준`이라는 문구가 있으면, 반복 금지사항은 이 문서의
   `Forbidden Boundaries`, `Strategy Evidence Loop Priority`,
   `Over-Engineering Control Principles`를 자동 적용한다.
3. 위험도가 낮은 read-only/audit/summary 작업은 새 지시문에 모든 필드와 모든
   금지사항을 길게 열거하지 않는다. 필요한 입력/출력만 명시한다.
4. collector, miniPC, runtime, shadow/live, secrets, payment, network collection,
   lock 파일, executor 경로처럼 위험한 작업만 명시적 금지사항을 짧게 반복한다.
5. 완료 보고는 아래 6개만 기본으로 한다.
   - 생성/수정 파일
   - 핵심 판정
   - 권한이 열리지 않았다는 근거
   - 검증 결과
   - 다음 safe patch candidate
   - 일반인용 요약
6. 같은 주제에서 contract -> preflight -> fixture -> closeout을 각각 따로
   만들 필요가 없으면 한 goal, 한 artifact로 묶는다. 단, runtime enablement,
   collector 실행, source append, shadow/live 연결 직전은 별도 승인 단계로
   분리한다.
7. 절차 artifact를 안전성 명목으로 과도하게 쪼개지 않는다. 다음 패턴은 기본적으로
   금지한다.
   - plan -> approval plan -> approval record -> checklist -> command review
     -> execution approval -> final command처럼 같은 결정을 4단계 이상으로
     나누는 것
   - 권한을 실제로 열지 않으면서 `approval`, `review`, `checklist`, `closeout`
     artifact만 반복 생성하는 것
   - 같은 금지사항을 새 artifact마다 다시 증명하는 것
8. 실제 위험 경계만 별도 승인 단계로 분리한다.
   - miniPC 실제 sync/ssh/rsync/scp
   - collector 실행 또는 network collection
   - source/outcome append 또는 ledger writer enablement
   - shadow/live/scanner/executor/promotion 연결
   - secrets/API key/payment/lock 파일 변경
   위 항목이 아니면 readiness, approval, command plan은 가능하면 한 artifact로
   합친다.
   단, 사용자가 같은 goal 안에서 명시적으로 실행을 승인한 경우에는
   discovery -> dry-run -> execution -> post-validation을 한 artifact와 한 작업
   흐름으로 묶을 수 있다. 이때도 dry-run 실패, 후보 0개/복수, secrets 필요,
   예상 밖의 mutation 위험이 있으면 실행하지 않고 멈춘다.
9. read-only/no-runtime 작업의 기본 형식은 `readiness_and_action_plan` 하나다.
   이 artifact 안에 필요한 경우 승인 상태, 체크리스트, 명령 후보, rollback,
   validation plan을 함께 둔다.
10. 운영값이 비어 있을 때는 먼저 안전한 자동 탐색을 검토한다. 예를 들어
    `<miniPC>` placeholder, remote project path, service name, artifact path는
    read-only discovery로 확인 가능하면 사용자에게 되묻기 전에 탐색한다. 단,
    secrets, password, payment, destructive operation, 후보 0개/복수처럼 자동
    확정이 위험한 경우에만 질문한다.
11. “대기”는 기본 답변이 아니다. 안전한 read-only 확인, dry-run, 자동 탐색,
    기존 runner 재실행, local validation으로 진전시킬 수 있으면 먼저 진행한다.
    대기는 row/linkage 변화가 실제로 없거나, 명시 승인/외부 상태 없이는 더
    진행할 수 없을 때만 선택한다.
12. 검증은 작업 위험도에 따라 차등화한다.
   - 문서/요약만 변경: grep 또는 focused test + 필요 시 validate
   - read-only artifact: py_compile + focused test
   - schema/helper/collector 영향: focused test + full direct tests +
     validate_current_state.py
   - GUI 영향: npm build + sync audit + screenshot check
   - runtime/collector 실행/배포 직전: full direct tests + validate +
     별도 manual approval artifact
13. 새 artifact를 만들 때마다 “이 artifact가 실제 row/linkage/confidence review를
   전진시키는가, 아니면 설명만 늘리는가”를 보고한다. 설명만 늘리면 다음 작업은
   통합/정리 또는 wait-state로 둔다.
14. 토큰 절약을 이유로 safety boundary를 생략하지 않는다. 다만 이미 이 문서에
   고정된 boundary는 반복하지 않고 참조한다.
15. 사용자가 “지시문을 짧게”, “토큰 아껴서”, “간단히”라고 말하면 위 축약 양식을
    우선 적용한다.

## State Recording

아래 문서에 진행상황을 누적 기록한다.

- `docs/NEXT_TASK.md`
- `docs/CURRENT_PROBLEM_STATUS.md`
- `docs/AUTO_GOAL_LOOP.md`
- 관련 control 문서
- 관련 strategy/replay/validation 문서

각 기록에는 다음을 포함한다.

- current phase
- completed block
- generated artifacts
- validation result
- remaining blockers
- next exact command
- stop condition 여부
- operator visibility 상태

## Auto Goal Loop / Next Goal Document

사용자가 “목표를 출력하지 말고 별도의 목표문서에 작성하고 다시 그 목표를
바로 실행해서 루프”하라고 지시한 경우, 다음 규칙을 적용한다.

1. 다음 목표는 final 답변에 길게 출력하지 않는다.
2. 다음 목표, 범위, 원칙, stop condition, next exact command는
   `docs/AUTO_GOAL_LOOP.md`에 기록한다.
3. 작업 블록 완료 후 다음 deterministic command가 있으면
   `docs/AUTO_GOAL_LOOP.md`, `docs/NEXT_TASK.md`,
   `docs/CURRENT_PROBLEM_STATUS.md`를 갱신하고 계속 진행한다.
4. 사용자가 방금 받은 목표/범위/원칙을 다시 보내면, 그것을 실행 트리거로
   보고 이 문서의 고정 루프를 적용한다.
5. “다음 목표 리스트”는 사용자가 명시적으로 요청한 경우에만 대화창에
   출력한다. 기본값은 문서 기록이다.
6. 루프는 아래 중 하나가 발생할 때 멈춘다.
   - Stage 4B cost-adjusted replay 실행 직전
   - shadow observe 연결 직전
   - strategy promotion 판단 직전
   - 사용자 판단이 필요한 blocker
   - 보안/실거래/live-order/secrets/API-key/유료결제/모델설치 이슈
   - bounded guard 없는 네트워크 수집 필요
   - 즉시 해결할 수 없는 validation 실패
7. Stage 4 descriptive/review-only 작업은 사용자가 승인한 경우 자동 루프에서
   진행할 수 있다.
8. Stage 4B cost-adjusted replay, shadow observe, strategy promotion,
   live/limited-live 전환 직전에는 자동으로 실행하지 말고 명시적 승인 필요
   상태로 문서에 남긴다.

## Forbidden Boundaries

- private secret configuration access remains forbidden
- scanner/executor/live/limited-live/shadow handoff/strategy promotion 연결 금지
- API key/secrets 입력 금지
- 유료 데이터 결제 금지
- 모델 설치/교체 금지
- 실거래 설정 변경 금지
- 실시간 매매 판단 로직 변경 금지
- bounded guard 없는 네트워크 수집 금지
- 수익 threshold mining 금지
- LLM을 진입/청산/사이징/승인 판단에 사용 금지
- 모든 작업은 research-only / no-execution artifact로 제한

## Stop Conditions

아래 상황에서만 멈추고 보고한다.

- 보안 위험
- 실거래/live-order 위험
- secrets/API-key 필요
- 유료 데이터 결제 필요
- 모델 설치/교체 필요
- 사용자 판단이 필요한 의사결정
- bounded guard 없는 네트워크 수집 필요
- validation 실패를 즉시 해결할 수 없는 경우

## Reporting Rule

단일 block, artifact, validation 통과는 final 보고 조건이 아니다.
다음 exact command가 있으면 계속 진행한다.

final 보고는 다음 경우에만 한다.

1. 사용자가 명시적으로 `멈춰`, `보고해`, `요약해`, `최종 보고해`라고
   요청한 경우
2. 중단 허용 조건에 해당하는 blocker가 발생한 경우
3. 지시한 전체 phase가 deterministic state 기준으로 완료 또는 명확한
   blocker 상태로 닫힌 경우
   
final 보고 시 보고 마지막에 다음 작업이 아닌 다음 양식으로 말한다.
목표:
[다음 작업 목표] 중요: 다음 작업 목표는 하나가 아닌 우선순위 기준으로 여러 개로 작성할 것(원칙 대목표 + 하위 phase ), 긴식간동안 할만한 목표로 작성할 것

범위: 
[다음 작업 범위]

원칙:
[다음 작업 원칙]

단, `Auto Goal Loop / Next Goal Document` 모드가 활성화된 경우에는 위
목표/범위/원칙을 대화창에 출력하지 않고 `docs/AUTO_GOAL_LOOP.md`에
기록한다. final 답변은 변경된 문서와 실행 트리거만 짧게 알린다.

## Short Invocation Template

앞으로 가장 짧은 실사용 지시문은 아래와 같다.

```text
goal

docs/GOAL_CONTROL.md 기준으로 진행해주세요.

목표:
[이번 작업 목표]

예시:
[원하는 산출물 또는 다음 단계 예시]
```

더 짧게는 아래처럼 보낼 수 있다.

```text
goal

docs/GOAL_CONTROL.md와 docs/NEXT_TASK.md 기준으로 다음 exact command부터
계속 진행해주세요.
```
