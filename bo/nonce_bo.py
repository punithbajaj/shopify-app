from src.connectors.shopify.repository.nonce_repository import NonceRepository
import uuid


class NonceBO:
    def __init__(self):
        self.repository = NonceRepository()

    def create(self, data):
        nonce = uuid.uuid4().hex
        document = {
            'nonce': nonce,
            'data': data,
        }
        self.repository.create(document)
        return nonce

    def get_by_data(self, data, state):
        return self.repository.get(data, state)

    def delete(self, nonce):
        self.repository.delete(nonce)




