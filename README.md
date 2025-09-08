# bmate-test-coding - Nguyễn Thanh Sang
# Hướng dẫn
##  Yêu cầu hệ thống
- Python >= 3.10  
- Git  
- (Khuyến nghị) Virtual environment (uv,venv, conda, poetry...)

---

##  Cài đặt

### 1. Clone project từ GitHub
```bash
git clone https://github.com/babygarlic/bmate-test-coding.git
cd bmate-test-coding
```
### 2. Tạo virtual environment
- Trên Windows:
```bash
python -m venv venv
venv\Scripts\activate
```
- Trên Linux/MacOS:
```bash
python3 -m venv venv
source venv/bin/activate
```
### 3. Cài đặt thư viện
### Do project dùng pyproject.toml, bạn có 2 cách cài:
#### Cách 1: Dùng pip install
```bash
pip install "beautifulsoup4>=4.13.5" "geopy>=2.4.1" "googletrans==4.0.0rc1" "requests>=2.32.5" "selenium>=4.35.0"
```
#### Cách 2: Dùng pip trực tiếp từ pyproject.toml
Bạn có thể dùng pip kèm theo pip-tools
 hoặc uv/poetry.
Ở đây mình hướng dẫn bằng uv (nhanh, nhẹ):
Cài uv:
```bash
pip install uv
```
Cài thư viện:
```bash
uv pip install -r pyproject.toml
```
### Thư viện sẽ bao gồm:
```bash
beautifulsoup4>=4.13.5

geopy>=2.4.1

googletrans==4.0.0rc1

requests>=2.32.5

selenium>=4.35.0
```
### 4. Chạy project
  Cấu trúc lệnh :
```
#python result.py -url <url cần lấy dữ liệu>
```
- Window: 
```bash
python result.py --url https://www.mitsui-chintai.co.jp/rf/tatemono/73689/101
```
- Trên Linux/MacOS:
```bash
python3 result.py --url https://www.mitsui-chintai.co.jp/rf/tatemono/73689/101
```
### 3. Lưu ý
   - Chương trình có sử dụng selenium nên trong quá trình chạy chương trình sẽ thao tác tự động mở trình duyệt nó sẽ tự động tắt sau khi hoàn thành lấy dữ liệu.
   - Các dữ liệu crawl sẽ được in ra terminal và cập nhật vào file CrawlData.json có thể xem lại dữ liệu sau khi crawl trong file này.
## Thông tin liên hệ
- Nguyễn Thanh Sang 
- email : thanhsang20031235@gmail.com
- zalo : 0583130289
