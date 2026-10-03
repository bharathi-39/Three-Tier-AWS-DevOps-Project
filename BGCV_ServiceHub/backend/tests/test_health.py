from app import create_app
def test_live():
    app=create_app(); app.config['TESTING']=True
    with app.test_client() as c:
        assert c.get('/api/health/live').status_code==200
