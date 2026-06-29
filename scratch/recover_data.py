import os
import re
import sys

def parse_varint(data, offset):
    """Parses a SQLite varint from data at the given offset."""
    val = 0
    for i in range(9):
        if offset + i >= len(data):
            break
        b = data[offset + i]
        val = (val << 7) | (b & 0x7F)
        if not (b & 0x80):
            return val, offset + i + 1
    return val, offset + 9

def get_serial_len(serial_type):
    """Returns the byte length of a SQLite serial type."""
    if serial_type == 0:
        return 0 # NULL
    elif serial_type == 1:
        return 1 # 8-bit int
    elif serial_type == 2:
        return 2 # 16-bit int
    elif serial_type == 3:
        return 3 # 24-bit int
    elif serial_type == 4:
        return 4 # 32-bit int
    elif serial_type == 5:
        return 6 # 48-bit int
    elif serial_type == 6:
        return 8 # 64-bit int
    elif serial_type == 7:
        return 8 # float
    elif serial_type == 8:
        return 0 # integer 0
    elif serial_type == 9:
        return 0 # integer 1
    elif serial_type == 10 or serial_type == 11:
        return 0 # reserved
    elif serial_type >= 12 and serial_type % 2 == 0:
        return (serial_type - 12) // 2 # BLOB
    elif serial_type >= 13 and serial_type % 2 == 1:
        return (serial_type - 13) // 2 # TEXT
    return 0

def recover_drafts():
    db_path = 'db.sqlite3'
    if not os.path.exists(db_path):
        print("db.sqlite3 not found!")
        return

    with open(db_path, 'rb') as f:
        data = f.read()

    print(f"Loaded db.sqlite3: {len(data)} bytes")

    # Column definition order for content_contentdraft:
    # ['id', 'platform', 'title', 'body', 'excerpt', 'meta_description', 'tags', 'word_count', 'status', 'reviewed_at', 'rejection_reason', 'ai_model', 'generation_prompt', 'created_at', 'updated_at', 'reviewed_by_id', 'website_id', 'idea_id', 'category', 'cover_image', 'is_deleted', 'author_name', 'custom_date', 'banner_settings']
    # That is 24 columns.
    
    # We will search for platform indicators: b'blog', b'linkedin', b'instagram', b'youtube'
    # which are common platform names in the 'platform' column (column index 1).
    # Since platform is column index 1, its value is very close to the header.
    
    # Let's search the database for occurrences of b'blog', b'linkedin', b'instagram', b'youtube'
    platforms = [b'blog', b'linkedin', b'instagram', b'youtube']
    recovered = []

    # Heuristic: search for cell headers
    # SQLite pages are typically 4096 bytes. Leaf pages start with 0x0D (leaf table b-tree page)
    page_size = 4096
    for page_idx in range(len(data) // page_size):
        page_start = page_idx * page_size
        page_data = data[page_start:page_start + page_size]
        if not page_data:
            continue
        
        # Check if it looks like a leaf table b-tree page (flag 0x0D)
        # Leaf pages start with 0x0D
        if page_data[0] != 0x0D:
            # We can also scan unallocated space on any page, so we don't strictly require 0x0D
            pass
            
        # Let's scan the raw bytes of the page for patterns of records
        # A record starts with header_size (varint)
        # Let's try to find headers by scanning byte-by-byte
        # Since we know the schema, a typical ContentDraft record header will contain 24 serial types.
        # Most of them will be text (serial type >= 13) or integers (0-9).
        # Let's scan for any block of bytes that can be parsed as a sequence of varints
        # representing 24 columns, where:
        # - col 1 (platform): length 4 to 9 (serial type 21 to 31)
        # - col 2 (title): text of length 10 to 300 (serial type 33 to 613)
        # - col 3 (body): text of length 100 to 20000 (serial type 213 to 40013)
        # - col 4 (excerpt): text of length 0 to 1000 (serial type 12 to 2013)
        
        offset = 0
        while offset < len(page_data) - 50:
            # Try parsing a record header
            hdr_size, next_off = parse_varint(page_data, offset)
            if hdr_size < 10 or hdr_size > 120 or next_off == offset:
                offset += 1
                continue
                
            # Parse serial types
            curr = next_off
            serial_types = []
            valid = True
            while curr - offset < hdr_size:
                st, next_curr = parse_varint(page_data, curr)
                if next_curr == curr:
                    valid = False
                    break
                serial_types.append(st)
                curr = next_curr
                
            if not valid or len(serial_types) < 18 or len(serial_types) > 26:
                offset += 1
                continue
                
            # Check if serial types match our schema signature:
            # col 1 (platform): st must represent a text of length 4-9 (serial type 21 to 31)
            # col 2 (title): st must represent a text of length 10-300 (serial type 33 to 613)
            # col 3 (body): st must represent a text of length 50-30000 (serial type 113 to 60013)
            if len(serial_types) >= 5:
                st_platform = serial_types[1]
                st_title = serial_types[2]
                st_body = serial_types[3]
                st_excerpt = serial_types[4]
                
                # Check platform text type
                is_plat_text = (st_platform >= 13 and st_platform % 2 == 1)
                is_title_text = (st_title >= 13 and st_title % 2 == 1)
                is_body_text = (st_body >= 13 and st_body % 2 == 1)
                
                if is_plat_text and is_title_text and is_body_text:
                    plat_len = get_serial_len(st_platform)
                    title_len = get_serial_len(st_title)
                    body_len = get_serial_len(st_body)
                    
                    if 3 <= plat_len <= 15 and 8 <= title_len <= 300 and 30 <= body_len <= 40000:
                        # This is highly likely a ContentDraft record!
                        # Let's extract the values
                        val_offset = offset + hdr_size
                        
                        try:
                            values = []
                            curr_val_off = val_offset
                            for st in serial_types:
                                l = get_serial_len(st)
                                val_bytes = page_data[curr_val_off:curr_val_off + l]
                                if len(val_bytes) < l:
                                    # Crosses page boundary or malformed
                                    # Since SQLite cell payloads can be split into overflow pages,
                                    # if it's very large, the body might be in overflow pages.
                                    # But let's retrieve whatever we can.
                                    pass
                                
                                if st >= 13 and st % 2 == 1:
                                    values.append(val_bytes.decode('utf-8', errors='replace'))
                                elif st == 0:
                                    values.append(None)
                                elif 1 <= st <= 6:
                                    # integer
                                    values.append(int.from_bytes(val_bytes, byteorder='big'))
                                elif st == 8:
                                    values.append(0)
                                elif st == 9:
                                    values.append(1)
                                else:
                                    values.append(val_bytes)
                                curr_val_off += l
                                
                            platform_val = values[1]
                            title_val = values[2]
                            body_val = values[3]
                            excerpt_val = values[4] if len(values) > 4 else ""
                            
                            # Let's check if this is about Devexhub or matches our interest
                            # If the body or title mentions Devexhub or other keywords, keep it!
                            if "devexhub" in str(body_val).lower() or "devexhub" in str(title_val).lower() or "aws" in str(title_val).lower() or "marketo" in str(title_val).lower():
                                recovered.append({
                                    'platform': platform_val,
                                    'title': title_val,
                                    'body': body_val,
                                    'excerpt': excerpt_val,
                                    'serial_types': serial_types
                                })
                        except Exception as e:
                            pass
            offset += 1

    # Remove duplicates by title
    unique_recovered = []
    seen_titles = set()
    for item in recovered:
        t = item['title'].strip()
        if t not in seen_titles:
            seen_titles.add(t)
            unique_recovered.append(item)

    print(f"\nRecovered {len(unique_recovered)} unique blogs from binary scanning!")
    
    os.makedirs('recovered_blogs', exist_ok=True)
    for idx, item in enumerate(unique_recovered, 1):
        filename = f"recovered_blogs/blog_{idx}.md"
        with open(filename, 'w', encoding='utf-8') as rf:
            rf.write(f"# {item['title']}\n\n")
            rf.write(f"**Platform:** {item['platform']}\n")
            rf.write(f"**Excerpt:** {item['excerpt']}\n\n")
            rf.write("## Content\n\n")
            rf.write(item['body'])
        print(f"Saved: {filename} - {item['title']}")

if __name__ == '__main__':
    recover_drafts()
