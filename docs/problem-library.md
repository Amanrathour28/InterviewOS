# Interview Problem Library Architecture

## Overview
Phase 9 introduces the **Interview Problem Library** to InterviewOS. It allows organizations to manage a curated repository of coding problems, system-level reference challenges, language starter templates, and test suites.

---

## 1. Multi-Tenant Library Model

```
                     Problem Library Root
                              │
             ┌────────────────┴────────────────┐
             │                                 │
     System Problems                   Workspace Problems
     (is_system = True)                (workspace_id = UUID)
             │                                 │
             ▼                                 ▼
   • Read-only to workspaces         • Private to workspace tenant
   • Seeded standard problems        • Authored by interviewers
   • Platform Admin managed          • Strict multi-tenant isolation
```

---

## 2. Problem Categories & Tagging

Problems are organized across standard algorithmic domains:
- `Arrays`, `Strings`, `Hashing`, `Two Pointers`, `Sliding Window`, `Stack`, `Queue`, `Linked List`, `Trees`, `Binary Search`, `Heap`, `Graphs`, `Dynamic Programming`, `Greedy`, `Backtracking`, `Recursion`, `Bit Manipulation`, `Math`, `SQL`, `Algorithms`, `Data Structures`.

Difficulties: `Easy`, `Medium`, `Hard`.

---

## 3. Cloning & Archiving

- **Problem Cloning**: Interviewers can clone both workspace and system problems into their workspace as independent problem definitions without affecting originals.
- **Problem Archiving**: Problems with historical usage are soft-archived (`status = 'archived'`), preserving backward compatibility for past interview reviews and reports while preventing new assignments.
