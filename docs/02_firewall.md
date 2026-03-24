# 02. 방화벽 오픈 목록

| 출발 | 목적지 | 포트 | 프로토콜 | 용도 |
|------|--------|------|----------|------|
| 포털 | Jenkins 마스터 | 8080 | TCP | Jenkins Job 트리거 |
| Jenkins 마스터 | GitLab | 443 | TCP | Jenkinsfile / repo checkout |
| Jenkins 마스터 | Agent | 22 | TCP | SSH — Agent 연결 |
| Agent | Jenkins 마스터 | 6379 | TCP | Redis Fact 캐싱 |
| Agent | 대상서버 Linux/ESXi | 22 | TCP | SSH |
| Agent | 대상서버 Windows | 5985/5986 | TCP | WinRM |
| Agent | 대상서버 Redfish | 443 | TCP | BMC HTTPS API |

> Redis(6379) 는 내부망만 오픈. 외부 차단 필수.
