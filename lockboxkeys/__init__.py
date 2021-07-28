import logging

import azure.functions as func

keys = {
    'source': 'sp=racwdl&st=2021-07-08T16:41:34Z&se=2025-01-02T01:41:34Z&spr=https&sv=2020-02-10&sr=c&sig=vw63LnLD3jszBewUPJF4GGpXUoAewJkN6OCoDmz2dsQ%3D',
    'dest': 'sp=rl&st=2021-07-26T15:11:55Z&se=2021-08-07T23:11:55Z&spr=https&sv=2020-08-04&sr=c&sig=rCOm8m3h7jjzMN3fcbTnfCLtTsXSpPeMDaBS1gOFN4k%3D',
    'audit': 'sp=r&st=2021-07-26T14:05:12Z&se=2021-08-07T22:05:12Z&spr=https&sv=2020-08-04&sr=c&sig=LyIWEpm2qAfAKSPK75wi3Ogeo4eRr9M8hLPfiPpNfp0%3D'
}


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.form.get('name')
    if name:
        return func.HttpResponse(keys[name])
    else:
        return func.HttpResponse(
            "Pass the name of the key to returned.", status_code=200
        )
