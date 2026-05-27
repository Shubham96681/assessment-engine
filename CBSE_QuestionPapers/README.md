# CBSE Mathematics Question Papers (Classes 6-12)

The assessment engine **indexes this folder automatically** in two ways:

1. **Quality floors** (class band: middle / secondary / senior) — `build_cbse_benchmark.py`
2. **Chapter/topic reference** (retrieved when user generates for a locked chapter) — `build_cbse_reference_index.py`

After adding PDFs, run from `backend/`:

```bash
python scripts/build_cbse_benchmark.py
python scripts/build_cbse_reference_index.py
```

Caches:
- `backend/data/cbse_benchmark/benchmark.json` — stem length / authenticity floors
- `backend/data/cbse_reference/manifest.json` — per-chapter stem counts
- `backend/data/faiss/cbse_reference/` — vector index for retrieval at generate time

On server start, both indexes rebuild automatically if PDFs are newer than the cache (`CBSE_*_AUTO_BUILD=true`).

API: `POST /api/v1/cbse/reference/build?force=true` · `GET /api/v1/cbse/reference/status`

## Downloaded Files (Desktop\CBSE_QuestionPapers\)

### Class 6
| File | Source |
|------|--------|
| `Class_06\Maths\CBE_All_Chapters.pdf` | CBSE Academic - Competency Based Items (full book) |

### Class 7
| File | Source |
|------|--------|
| `Class_07\Maths\CBE_All_Chapters.pdf` | CBSE Academic - Competency Based Items (full book, all chapters) |

### Class 8
| File | Source |
|------|--------|
| `Class_08\Maths\CBE_All_Chapters.pdf` | CBSE Academic - Competency Based Items (full book, all chapters) |

### Class 9
| File | Source |
|------|--------|
| `Class_09\Maths\CBE_All_Chapters.pdf` | CBSE Academic - Competency Based Items (full book, all chapters) |
| `Class_09\Maths\Teacher_Resource_Manual.pdf` | CBSE TERM - Chapter-wise questions & activities |

### Class 10
| File | Source |
|------|--------|
| `Class_10\Maths\Standard_SQP_2024_25.pdf` | CBSE Sample Paper - Maths Standard |
| `Class_10\Maths\Standard_SQP_2025_26.pdf` | CBSE Sample Paper - Maths Standard (latest) |
| `Class_10\Maths\Standard_MS_2024_25.pdf` | CBSE Marking Scheme - Standard |
| `Class_10\Maths\Standard_MS_2025_26.pdf` | CBSE Marking Scheme - Standard (latest) |
| `Class_10\Maths\Basic_SQP_2024_25.pdf` | CBSE Sample Paper - Maths Basic |
| `Class_10\Maths\Basic_MS_2024_25.pdf` | CBSE Marking Scheme - Basic |
| `Class_10\Maths\CBE_All_Chapters.pdf` | CBSE Academic - Competency Based Items |
| `Class_10\Maths\Teacher_Resource_Manual.pdf` | CBSE TERM - Chapter-wise questions & activities |

### Class 11
| File | Source |
|------|--------|
| *(No direct CBSE official SQP for Class 11 - see links below)* | |

### Class 12
| File | Source |
|------|--------|
| `Class_12\Maths\SQP_2023_24.pdf` | CBSE Sample Paper 2023-24 |
| `Class_12\Maths\SQP_2024_25.pdf` | CBSE Sample Paper 2024-25 |
| `Class_12\Maths\SQP_2025_26.pdf` | CBSE Sample Paper 2025-26 (latest) |
| `Class_12\Maths\MS_2024_25.pdf` | CBSE Marking Scheme 2024-25 |

---

## Online Resources for Chapter-wise Question Papers

### Official CBSE Academic Portal
- **CBSE CBE (Competency Based Education) Items**: https://cbseacademic.nic.in/cbe.html
- **Sample Papers Class 10 & 12**: https://cbseacademic.nic.in/SQP_CLASSX_2025-26.html / https://cbseacademic.nic.in/SQP_CLASSXII_2025-26.html
- **Previous Year Question Papers**: https://cbse.gov.in (Board Examinations > Previous Year QPs)

### Class 12 - Chapter-wise PYQs (Most Comprehensive)
| Resource | Link |
|----------|------|
| SelfStudys - 11 Years Ch-wise Solved | https://www.selfstudys.com/update/211954 |
| Slideshare - Topic-wise PYQs 2014-2023 | https://www.slideshare.net/slideshow/class-12-maths-cbse-pyq-chapter-wise-topic-wise-pdf/272430486 |
| CBSE Guidance - PYQs with Solutions | https://www.cbseguidanceweb.com/cbse-class-12-maths-pyqs-with-solutions-pdf/ |
| Vedantu - Year-wise Papers (2014-2025) | https://www.vedantu.com/previous-year-question-paper/cbse-class-12-maths-question-paper-2024 |
| GetMyUni - Year-wise PDFs | https://getmyuni.com/boards/cbse-class-12-mathematics-previous-year-question-papers |
| Arihant Ch-wise Question Bank (2026) | https://readyourflow.com/download-arihant-cbse-chapterwise-question-bank-maths-class-12-pdf/ |

### Class 10 - Chapter-wise Resources
| Resource | Link |
|----------|------|
| CBSE Guidance - PYQs with Solutions | https://www.cbseguidanceweb.com/cbse-class-10-maths-pyqs/ |
| Vedantu - Year-wise Papers | https://www.vedantu.com/previous-year-question-paper/cbse-class-10-maths-question-paper |
| SelfStudys - Chapter-wise Papers | https://www.selfstudys.com/books/cbse-prev-paper/english/class-10th |

### Class 9 - Sample Papers
| Resource | Link |
|----------|------|
| Jagran Josh - Sample Paper 2025 | https://www.jagranjosh.com/articles/cbse-class-9-maths-sample-paper-with-solutions-2024-2025-1737980187-1 |
| SelfStudys - Multiple Sets | https://www.selfstudys.com/books/cbse-sample-paper/english/9th |
| KopyKitab - 10 Sample Papers | https://www.kopykitab.com/blog/cbse-class-9-maths-sample-papers/ |

### Class 7 & 8 - Sample Papers
| Resource | Link |
|----------|------|
| BYJU'S - Class 7 Sample Papers | https://byjus.com/cbse-sample-paper-for-class-7-maths/ |
| BYJU'S - Class 8 Sample Papers | https://byjus.com/cbse-sample-paper-for-class-8-maths/ |

### How to Download from SelfStudys
1. Go to https://www.selfstudys.com
2. Search for "CBSE Class X Mathematics Chapter Wise"
3. Each chapter has individual download links
4. Registration may be required
