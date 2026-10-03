from .extensions import db
from .models import Ticket,Comment
VALID_PRIORITY={'LOW','MEDIUM','HIGH','CRITICAL'}; VALID_STATUS={'NEW','ASSIGNED','IN_PROGRESS','RESOLVED','CLOSED'}
def validate(payload,partial=False):
    errors={}
    for f in ('title','description','priority','created_by'):
        if not partial and not payload.get(f): errors[f]=f'{f.replace("_"," ").title()} is required'
    if payload.get('priority') and payload['priority'] not in VALID_PRIORITY: errors['priority']='Invalid priority'
    if payload.get('status') and payload['status'] not in VALID_STATUS: errors['status']='Invalid status'
    return errors
def ticket_json(t):
    return {'id':t.id,'ticket_number':t.ticket_number,'title':t.title,'description':t.description,'priority':t.priority,'status':t.status,'created_by':t.created_by,'created_by_name':t.creator.name if t.creator else None,'created_at':t.created_at.isoformat(),'updated_at':t.updated_at.isoformat(),'comments':[{'id':c.id,'comment':c.comment,'author':c.author,'created_at':c.created_at.isoformat()} for c in t.comments]}
def create_ticket(payload):
    t=Ticket(title=payload['title'].strip(),description=payload['description'].strip(),priority=payload['priority'],status=payload.get('status','NEW'),created_by=payload['created_by']); db.session.add(t); db.session.flush(); t.ticket_number=f'INC{t.id:04d}'; db.session.commit(); return t
def update_ticket(t,payload):
    for key in ('title','description','priority','status','created_by'):
        if key in payload: setattr(t,key,payload[key])
    db.session.commit(); return t
