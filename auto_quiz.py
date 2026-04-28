"""
auto_quiz.py – Tự động hoá trắc nghiệm bằng Playwright

Hướng dẫn:
  1. Cài đặt:  pip install -r requirements.txt && python -m playwright install chromium
  2. Điền thông tin vào questions_data.py
  3. Chạy:     python auto_quiz.py
  4. Trình duyệt mở ra, bạn nhập thông tin, click nút vào thi. Script sẽ tự động nhận diện
     khi trang thi load xong và bắt đầu trả lời câu hỏi.
"""

from playwright.sync_api import sync_playwright
import json
import sys
import time
from difflib import SequenceMatcher
import os
from dotenv import load_dotenv

# Tải các biến môi trường từ file .env nếu có
load_dotenv()

# Thiết lập encoding UTF-8 cho terminal Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ═══════════════════════════════════════════════════════════════════════════════
# CẤU HÌNH 
# ═══════════════════════════════════════════════════════════════════════════════

QUIZ_URL = "https://thitructuyen.vnmac.gov.vn/"

# ── XPath Template cho câu hỏi & đáp án ──────────────────────────────────────
# Câu hỏi dạng: /html/body/div/div[2]/div[2]/div[2]/div/div[1]/div[{q}]/div[1]
XPATH_QUESTION_TEXT = "/html/body/div/div[2]/div[2]/div[2]/div/div[1]/div[{q}]/div[1]"

# Đáp án dạng: /html/body/div/div[2]/div[2]/div[2]/div/div[1]/div[{q}]/div[2]/ul/li[{a}]
XPATH_OPTION_TEXT   = "/html/body/div/div[2]/div[2]/div[2]/div/div[1]/div[{q}]/div[2]/ul/li[{a}]"
XPATH_OPTION_CLICK  = "/html/body/div/div[2]/div[2]/div[2]/div/div[1]/div[{q}]/div[2]/ul/li[{a}]"

MAX_QUESTIONS_PER_PAGE = 15  # Số câu hỏi tối đa trên 1 trang (để vòng lặp tự quét)
MAX_OPTIONS            = 10   # Số đáp án tối đa mỗi câu (script sẽ tự check, ko có thì bỏ qua)

# XPath nút Vào thi để script theo dõi khi nào user click
XPATH_BTN_JOIN = "/html/body/div/div[2]/div[2]/div/form/button"

try:
    from questions_data import QUESTIONS_DATA  # type: ignore
except Exception as e:
    print(f"⚠️ Cảnh báo: Lỗi khi đọc file questions_data.py: {e}")
    QUESTIONS_DATA = []

FUZZY_MATCH_THRESHOLD    = 0.60  # Giảm xuống 0.6 để nhạy hơn

def normalize(text: str) -> str:
    """Chuẩn hoá text: bỏ khoảng trắng thừa, lowercase, bỏ dấu câu cuối dòng."""
    import re
    if not text: return ""
    # Chuyển về lowercase
    t = text.strip().lower()
    # Loại bỏ dấu câu ở cuối (chấm, phẩy, hai chấm...)
    t = re.sub(r'[.\-:,;!?]+$', '', t)
    # Loại bỏ khoảng trắng thừa ở giữa
    return " ".join(t.split())

def fuzzy_match(text_a: str, text_b: str) -> float:
    """Trả về độ tương đồng giữa 2 chuỗi."""
    return SequenceMatcher(None, normalize(text_a), normalize(text_b)).ratio()

def build_question_index(questions: list) -> list[tuple[str, dict]]:
    return [(normalize(item.get("question", "")), item) for item in questions]

def find_matching_question(page_question_text: str, question_index: list[tuple[str, dict]]) -> dict | None:
    norm_page = normalize(page_question_text)
    best_match = None
    best_score = 0.0

    for norm_q, item in question_index:
        if not norm_q: continue # Bỏ qua câu hỏi rỗng trong data
        
        if norm_page == norm_q:
            return item
        
        # Chỉ tính điểm substring nếu chuỗi không rỗng
        if norm_q in norm_page or norm_page in norm_q:
            score = max(SequenceMatcher(None, norm_page, norm_q).ratio(), 0.85)
        else:
            score = SequenceMatcher(None, norm_page, norm_q).ratio()
        if score > best_score:
            best_score = score
            best_match = item

    if best_score >= FUZZY_MATCH_THRESHOLD:
        return best_match

    return None

def answer_all_questions(page, questions: list) -> dict:
    q_index = build_question_index(questions)
    print(f"\n📋 Bắt đầu trả lời (data có {len(questions)} câu)...\n")

    results = {
        "total_in_data": len(questions),
        "answered": 0,
        "skipped": [],
    }

    for q_idx in range(1, MAX_QUESTIONS_PER_PAGE + 1):
        # Đọc text câu hỏi
        q_xpath = XPATH_QUESTION_TEXT.replace("{q}", str(q_idx))
        try:
            page_question_text = page.evaluate("""async (xpath) => {
                const el = document.evaluate(xpath, document, null, 9, null).singleNodeValue;
                if (el && (el.textContent || "").trim().length > 0) {
                    try { if (el.scrollIntoViewIfNeeded) el.scrollIntoViewIfNeeded(); } catch(e){}
                    return (el.textContent || "").trim();
                }
                return null;
            }""", q_xpath)
        except Exception:
            page_question_text = None

        if not page_question_text:
            # Không thấy câu hỏi tiếp theo -> dừng (hết câu hỏi)
            break

        q_short = page_question_text[:70] + ("..." if len(page_question_text) > 70 else "")
        print(f"\n{'─' * 50}")
        print(f"  📌 Câu {q_idx}: {q_short}")

        matched_item = find_matching_question(page_question_text, q_index)

        if not matched_item:
            print(f"     ❌ Không tìm thấy trong data – BỎ QUA")
            results["skipped"].append(page_question_text)
            continue

        expected_answer = matched_item.get("answer", "").strip()
        norm_answer = normalize(expected_answer)
        print(f"     🔍 Đáp án cần tìm: \"{expected_answer[:60]}{'...' if len(expected_answer) > 60 else ''}\"")

        # Đọc tất cả đáp án của câu hỏi
        js_xpaths = [
            XPATH_OPTION_TEXT.replace("{q}", str(q_idx)).replace("{a}", str(i))
            for i in range(1, MAX_OPTIONS + 1)
        ]
        
        try:
            option_texts = page.evaluate("""(xpaths) => {
                return xpaths.map(xp => {
                    const el = document.evaluate(xp, document, null, 9, null).singleNodeValue;
                    return el ? (el.textContent || el.innerText || "").trim() : "";
                });
            }""", js_xpaths)
        except Exception:
            option_texts = []
            
        if not any(option_texts):
            print(f"     ❌ Đáp án trống (web chưa trả về) – BỎ QUA")
            results["skipped"].append(page_question_text)
            continue

        best_a_idx = -1
        best_a_score = 0.0

        # Nếu một câu hỏi có nhiều đáp án đúng thì logic dưới đây sẽ chọn đáp án khớp nhất.
        # Nếu muốn click nhiều đáp án cho 1 câu (ví dụ checkbox), bạn có thể sửa lại vòng lặp.
        for i, option_text in enumerate(option_texts):
            if not option_text:
                continue
            a_idx = i + 1
            
            # Xoá prefix dạng "A.", "1.", "a)", "1)" ở đầu chuỗi (nếu có)
            import re
            clean_opt = re.sub(r'^[a-zA-Z0-9][.)]\s*', '', option_text).strip()
                
            norm_opt = normalize(clean_opt)

            if not norm_answer:
                score = 0.0
            elif norm_opt == norm_answer:
                score = 1.0
            elif norm_answer in norm_opt or norm_opt in norm_answer:
                score = 0.85
            else:
                score = SequenceMatcher(None, norm_opt, norm_answer).ratio()

            opt_short = clean_opt[:50] + ("..." if len(clean_opt) > 50 else "")
            print(f"       [{a_idx}] \"{opt_short}\" (match: {score:.0%})")

            if score > best_a_score:
                best_a_score = score
                best_a_idx = a_idx

            if best_a_score == 1.0:
                break 

        found = False
        if best_a_idx > 0 and best_a_score >= FUZZY_MATCH_THRESHOLD:
            click_xpath = XPATH_OPTION_CLICK.replace("{q}", str(q_idx)).replace("{a}", str(best_a_idx))

            try:
                # Dùng JS click thẳng vào element và kích hoạt cả các con (input, span) bên trong
                page.evaluate(f"""(xpath) => {{
                    const el = document.evaluate(xpath, document, null, 9, null).singleNodeValue;
                    if (el) {{
                        el.click();
                        // Click thêm vào input hoặc span bên trong li để đảm bảo kích hoạt radio/checkbox
                        const sub = el.querySelector('input, span, label');
                        if (sub) sub.click();
                    }}
                }}""", click_xpath)
                found = True
                print(f"     ✅ Đã chọn đáp án [{best_a_idx}] (score: {best_a_score:.0%})")
                page.wait_for_timeout(300) # Đợi một chút để UI cập nhật
            except Exception as e:
                print(f"     ⚠️  Lỗi click: {e}")

        if not found:
            print(f"     ❌ Không khớp đáp án nào – BỎ QUA")
            results["skipped"].append(page_question_text)
        else:
            results["answered"] += 1

    return results

def print_report(results: dict):
    skipped_count = len(results["skipped"])
    total_on_exam = results["answered"] + skipped_count

    print("\n  ✅ Hoàn tất tự động trả lời")
    print("  ══════════════════════════════════════")
    print(f"  Tổng câu trong data     : {results['total_in_data']}")
    print(f"  Câu hỏi xuất hiện trên đề: {total_on_exam}")
    print(f"  Đã trả lời thành công   : {results['answered']}")
    print(f"  Không có trong data/đáp án: {skipped_count}")

    if results["skipped"]:
        print(f"  Câu bị bỏ qua           :")
        for sq in results["skipped"]:
            sq_short = sq[:70] + ("..." if len(sq) > 70 else "")
            print(f"    • {sq_short}")
    print("  ══════════════════════════════════════\n")

def main():
    print("╔══════════════════════════════════════════╗")
    print("║   AUTO QUIZ – Playwright Automation      ║")
    print("╚══════════════════════════════════════════╝\n")

    questions = QUESTIONS_DATA
    if not questions:
        print("❌ Không có dữ liệu câu hỏi! Kiểm tra file questions_data.py")
        sys.exit(1)

    print(f"📊 Tổng số câu hỏi trong kho data: {len(questions)}")

    with sync_playwright() as pw:
        print("\n🌐 Khởi động trình duyệt...")
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="vi-VN",
        )
        page = context.new_page()
        page.set_default_timeout(15000)

        try:
            print(f"\n📝 Mở trang: {QUIZ_URL}")
            page.goto(QUIZ_URL, wait_until="domcontentloaded")
            
            print("\n⏳ Vui lòng nhập thông tin trên trình duyệt và ấn nút tham gia thi.")
            print("   Script đang đợi câu hỏi xuất hiện để bắt đầu...\n")
            
            # Đợi cho đến khi câu hỏi đầu tiên xuất hiện trên trang
            first_q_xpath = XPATH_QUESTION_TEXT.replace("{q}", "1")
            
            last_logged_url = ""
            while True:
                if page.is_closed():
                    sys.exit(0)
                
                try:
                    current_url = page.url
                    if current_url != last_logged_url:
                        print(f"🌐 URL hiện tại: {current_url}")
                        last_logged_url = current_url

                    # Kiểm tra xem đã vào trang thi chưa (không phân biệt hoa thường)
                    is_baithi_url = "/baithi" in current_url.lower()
                    
                    # Kiểm tra xem câu hỏi đã xuất hiện chưa
                    q_exists = page.evaluate(f"""(xpath) => {{
                        const q = document.evaluate(xpath, document, null, 9, null).singleNodeValue;
                        return !!q && (q.textContent || "").trim().length > 0;
                    }}""", first_q_xpath)
                    
                    # Nếu thấy câu hỏi xuất hiện, hoặc URL đã đúng trang thi thì bắt đầu
                    if q_exists or is_baithi_url:
                        if q_exists:
                            print(f"🚀 Đã phát hiện câu hỏi trên trang!")
                            print("   Đang đợi trang ổn định (3s)...")
                            page.wait_for_load_state("domcontentloaded")
                            page.wait_for_timeout(3000)
                            break
                        elif is_baithi_url:
                            # Đã đúng URL nhưng chưa thấy câu hỏi, đợi thêm chút
                            pass
                except Exception:
                    pass
                    
                time.sleep(1)
            
            # Thực hiện trả lời
            results = answer_all_questions(page, questions)
            print_report(results)

            print("💡 Trình duyệt đang mở để bạn kiểm tra lại đáp án và TỰ NỘP BÀI.")
            print("   Nhấn Ctrl+C ở terminal này để đóng trình duyệt.")
            
            # Giữ trình duyệt mở cho người dùng tự thao tác nộp bài
            try:
                while not page.is_closed():
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

        except Exception as e:
            if "Target closed" in str(e) or "Browser.close" in str(e) or "Target page, context" in str(e) or "Connection closed" in str(e):
                print("\n👋 Bạn đã đóng trình duyệt.")
            else:
                print(f"\n❌ LỖI: {e}")
                import traceback
                traceback.print_exc()

        finally:
            context.close()
            browser.close()
            print("🏁 Đã đóng. Tạm biệt!")

if __name__ == "__main__":
    main()
