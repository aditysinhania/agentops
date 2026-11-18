from conftest import auth, register


def test_owner_can_update_and_delete_datasets_and_cases(client):
    account = register(client)
    headers = auth(account['access_token'])
    dataset = client.post('/api/datasets', headers=headers, json={'name': 'CRUD cases', 'description': 'Original'}).json()
    updated_dataset = client.patch(f"/api/datasets/{dataset['id']}", headers=headers, json={'name': 'Reviewed cases'}).json()
    assert updated_dataset['name'] == 'Reviewed cases'
    case = client.post(f"/api/datasets/{dataset['id']}/cases", headers=headers, json={
        'input': 'question', 'expected_output': 'expected', 'actual_output': 'draft', 'metadata': {'source': 'unit-test'}
    }).json()
    assert case['metadata_json'] == {'source': 'unit-test'}
    updated_case = client.patch(f"/api/datasets/{dataset['id']}/cases/{case['id']}", headers=headers, json={'actual_output': 'answer'})
    assert updated_case.status_code == 200
    assert updated_case.json()['actual_output'] == 'answer'
    deleted_case = client.delete(f"/api/datasets/{dataset['id']}/cases/{case['id']}", headers=headers)
    assert deleted_case.status_code == 204
    assert client.get(f"/api/datasets/{dataset['id']}", headers=headers).json()['cases'] == []
    assert client.patch(f"/api/datasets/{dataset['id']}", headers=headers, json={}).status_code == 422
    assert client.delete(f"/api/datasets/{dataset['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/datasets/{dataset['id']}", headers=headers).status_code == 404


def test_dataset_and_case_mutations_are_user_scoped(client):
    first = register(client, 'dataset-owner@example.com')
    second = register(client, 'dataset-guest@example.com')
    dataset = client.post('/api/datasets', headers=auth(first['access_token']), json={'name': 'Private dataset'}).json()
    case = client.post(f"/api/datasets/{dataset['id']}/cases", headers=auth(first['access_token']), json={'input': 'question'}).json()
    guest_headers = auth(second['access_token'])
    assert client.patch(f"/api/datasets/{dataset['id']}", headers=guest_headers, json={'name': 'Hijacked'}).status_code == 404
    assert client.delete(f"/api/datasets/{dataset['id']}/cases/{case['id']}", headers=guest_headers).status_code == 404
    assert client.delete(f"/api/datasets/{dataset['id']}", headers=guest_headers).status_code == 404
