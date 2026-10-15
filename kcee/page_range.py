def validate_page_range(document_id,start,end):
    if start is None and end is None:return None
    if not document_id or type(start) is not int or type(end) is not int or not 1<=start<=end<=300:raise ValueError('Choose a PDF and both page bounds, from 1 to 300, in ascending order')
    return {'start':start,'end':end}
