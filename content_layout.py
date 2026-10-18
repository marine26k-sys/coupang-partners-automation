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
    if len(lines)<2:return copy.strip()
    intro=lines[0]
    checks=[line.lstrip('·•- ') for line in lines[1:]]
    if not any(c in copy for c in ALLOWED_EMOJI):checks[0]='✅ '+checks[0].lstrip('·•- ')
    checks=[line if index==0 or line.startswith(('·','•','✅','📌','🔎','🧺')) else '· '+line for index,line in enumerate(checks)]
    return intro+'\n\n'+'\n'.join(checks)


def blog_section(heading, body, index):
    validate_emoji(heading,1);validate_emoji(body,0)
    if not any(c in heading for c in ALLOWED_EMOJI):heading=['🧺','📌','🔎'][index]+' '+heading
    # Sentence blocks stay separate in the editor rather than one long paragraph.
    return heading, sentences(body)
