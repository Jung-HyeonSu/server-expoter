# 01. VM 리소스 산정

## Jenkins 마스터

| 항목 | 사양 |
|------|------|
| CPU | 8 core |
| RAM | 32 GB (Jenkins 16GB + Redis 1GB + 여유) |
| Disk | 500 GB (빌드 로그, 히스토리 누적 고려) |

## Jenkins Agent

| 항목 | 사양 |
|------|------|
| CPU | 8 core |
| RAM | 16 GB |
| Disk | 100 GB (Ansible 가상환경 + workspace) |

## Redis (마스터 노드에 함께 설치)

호스트 약 1만 대 기준:

```
호스트당 facts 평균 20~50KB × 10,000대 = 200~500MB
여유분 포함 → maxmemory 1GB
eviction policy: allkeys-lru
fact_caching_timeout: 86400 (24시간)
```

```ini
# /etc/redis.conf
maxmemory 1gb
maxmemory-policy allkeys-lru
```
