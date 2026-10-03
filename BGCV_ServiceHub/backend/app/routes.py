from flask import Blueprint,request
from sqlalchemy import or_,func,text
from .extensions import db
from .models import Ticket,User,Comment
from .services import validate,create_ticket,update_ticket,ticket_json
api=Blueprint('api',__name__,url_prefix='/api')
def ok(data=None,message='OK',status=200): return {'success':True,'data':data,'message':message},status
def fail(code,message,status=400,details=None): return {'success':False,'error':{'code':code,'message':message,'details':details}},status
@api.get('/health')
@api.get('/health/live')
def live(): return ok({'status':'healthy'},'Service is live')
@api.get('/health/ready')
def ready():
    try: db.session.execute(text('SELECT 1')); return ok({'status':'ready','database':'connected'},'Service is ready')
    except Exception: return fail('NOT_READY','Database unavailable',503)
@api.get('/users')
def users(): return ok([{'id':u.id,'name':u.name,'email':u.email,'role':u.role} for u in User.query.order_by(User.name).all()])
@api.get('/tickets')
def tickets():
    q=Ticket.query; search=request.args.get('search','').strip(); status=request.args.get('status'); priority=request.args.get('priority'); page=max(request.args.get('page',1,type=int),1); size=min(request.args.get('size',10,type=int),50)
    if search: q=q.filter(or_(Ticket.title.ilike(f'%{search}%'),Ticket.ticket_number.ilike(f'%{search}%')))
    if status: q=q.filter_by(status=status)
    if priority: q=q.filter_by(priority=priority)
    p=q.order_by(Ticket.created_at.desc()).paginate(page=page,per_page=size,error_out=False)
    return ok({'items':[ticket_json(x) for x in p.items],'pagination':{'page':page,'size':size,'total':p.total,'pages':p.pages}})
@api.get('/tickets/<int:ticket_id>')
def get_ticket(ticket_id):
    t=db.get_or_404(Ticket,ticket_id); return ok(ticket_json(t))
@api.post('/tickets')
def post_ticket():
    data=request.get_json(silent=True) or {}; errors=validate(data)
    if errors:return fail('VALIDATION_ERROR','Please correct the highlighted fields',422,errors)
    return ok(ticket_json(create_ticket(data)),'Ticket created successfully',201)
@api.put('/tickets/<int:ticket_id>')
def put_ticket(ticket_id):
    t=db.get_or_404(Ticket,ticket_id); data=request.get_json(silent=True) or {}; errors=validate(data,True)
    if errors:return fail('VALIDATION_ERROR','Invalid ticket data',422,errors)
    return ok(ticket_json(update_ticket(t,data)),'Ticket updated successfully')
@api.delete('/tickets/<int:ticket_id>')
def delete_ticket(ticket_id):
    t=db.get_or_404(Ticket,ticket_id); db.session.delete(t); db.session.commit(); return ok(None,'Ticket deleted successfully')
@api.post('/tickets/<int:ticket_id>/comments')
def add_comment(ticket_id):
    t=db.get_or_404(Ticket,ticket_id); data=request.get_json(silent=True) or {}
    if not data.get('comment','').strip(): return fail('VALIDATION_ERROR','Comment is required',422)
    c=Comment(ticket_id=t.id,comment=data['comment'].strip(),author=data.get('author','Admin')); db.session.add(c); db.session.commit(); return ok(ticket_json(t),'Comment added',201)
@api.get('/dashboard/stats')
def stats():
    total=Ticket.query.count(); by_status=dict(db.session.query(Ticket.status,func.count(Ticket.id)).group_by(Ticket.status)); by_priority=dict(db.session.query(Ticket.priority,func.count(Ticket.id)).group_by(Ticket.priority))
    return ok({'total':total,'open':sum(by_status.get(x,0) for x in ['NEW','ASSIGNED','IN_PROGRESS']),'resolved':by_status.get('RESOLVED',0),'critical':by_priority.get('CRITICAL',0),'by_status':by_status,'by_priority':by_priority})
