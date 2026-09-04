# Server-Authoritative Interview State Machine (Phase 11)

InterviewOS enforces a deterministic, server-authoritative state lifecycle across all interview rooms.

---

## 1. State Diagram

```
                 +-------------------+
                 |      WAITING      |
                 +-------------------+
                           |
                     (start_session)
                           |
                           v
                 +-------------------+
        +------->|      ACTIVE       |<------+
        |        +-------------------+       |
 (resume_session)          |           (pause_session)
        |                  v                 |
        +--------+-------------------+-------+
                 |      PAUSED       |
                 +-------------------+
                           |
                      (end_session)
                           |
                           v
                 +-------------------+
                 |     COMPLETED     |
                 +-------------------+
```

---

## 2. Server-Side Calculations

1. **Elapsed Seconds Calculation**:
   $$\text{raw\_duration} = \begin{cases} 
   \text{ended\_at} - \text{started\_at}, & \text{if COMPLETED} \\
   \text{paused\_at} - \text{started\_at}, & \text{if PAUSED} \\
   \text{now\_utc} - \text{started\_at}, & \text{if ACTIVE}
   \end{cases}$$
   $$\text{elapsed\_seconds} = \max(0, \text{int}(\text{raw\_duration}) - \text{total\_paused\_seconds})$$

2. **Remaining Seconds Calculation**:
   $$\text{remaining\_seconds} = \max(0, (\text{duration\_minutes} \times 60) - \text{elapsed\_seconds})$$

3. **Stage Elapsed Seconds Calculation**:
   $$\text{stage\_elapsed\_seconds} = \max(0, \text{int}(\text{current\_time} - \text{stage\_started\_at}))$$

---

## 3. State Constraints

- `WAITING` sessions cannot be paused or resumed.
- `PAUSED` sessions cannot be paused again.
- `ACTIVE` sessions cannot be resumed again.
- `COMPLETED` sessions are immutable and cannot be restarted.
