"""Readable Korean post layout with restrained structural emoji."""
import re

ALLOWED_EMOJI={'✅','📌','🔎','🧺'}


def validate_emoji(text, maximum):
    marks=[c for c in text if 0x1F300<=ord(c)<=0x1FAFF or 0x2600<=ord(c)<=0x27BF]
    if any(c not in ALLOWED_EMOJI for c in marks) or len(marks)>maximum:
        raise ValueError('이모지는 구분용으로만 제한해 사용하세요.')


def sentences(text):
    return [x.strip() for x in re.split(r'(?<=[.!?])\s+|\n+',text.strip()) if x.strip()]


def threads_layout(copy):
    validate_emoji(copy,2)
    lines=sentences(copy)
    cleaned=[]
    for line in lines:
        line=re.sub(r'^[·•.]\s+', '', line).strip()
        if not line.startswith(('https://','http://')):
            line=re.sub(r'[.。]+$', '', line).rstrip()
        if line:cleaned.append(line)
    return '\n\n'.join(cleaned)



def blog_section(heading, body, index):
    validate_emoji(heading,1);validate_emoji(body,0)
    if not any(c in heading for c in ALLOWED_EMOJI):heading=['🧺','📌','🔎'][index]+' '+heading
    # Sentence blocks stay separate in the editor rather than one long paragraph.
    return heading, sentences(body)


def mobile_blog_html(markup):
    """Explicit small body text and real empty paragraphs survive editor paste."""
    markup=re.sub(r'<h2><strong>(.*?)</strong></h2>',r'<p><span style="font-size:16px"><b>\1</b></span></p>',markup)
    markup=re.sub(r'<p>(?!<span)', '<p><span style="font-size:14px">',markup)
    markup=re.sub(r'(?<!</span>)</p>', '</span></p>',markup)
    return markup.replace('</p>','</p><p><br></p>')
