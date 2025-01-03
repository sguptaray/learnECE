import argparse
import numpy as np
import pickle
import time
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from copy import deepcopy
import sklearn
import sklearn.metrics

import transformer.Constants as Constants


from preprocess.Dataset import get_dataloader
from transformer.Baseline import Transformer
from tqdm import tqdm
import seaborn as sns
    


def prepare_dataloader(opt):
    """ Load data and prepare dataloader. """

    def load_data(name, dict_name):
        with open(name, 'rb') as f:
            data = pickle.load(f, encoding='latin-1')
            num_types = data['dim_process']
            data = data[dict_name]
            return data, int(num_types)

    print('[Info] Loading train data...')
    train_data, num_types = load_data(opt.data + 'train.pkl', 'train')
    print('[Info] Loading dev data...')
    dev_data, _ = load_data(opt.data + 'dev.pkl', 'dev')
    print('[Info] Loading test data...')
    test_data, _ = load_data(opt.data + 'test.pkl', 'test')

    trainloader = get_dataloader(train_data, opt.batch_size, shuffle=True)
    devloader = get_dataloader(dev_data, opt.batch_size, shuffle=True)
    testloader = get_dataloader(test_data, opt.batch_size, shuffle=False)
    return trainloader, devloader, testloader, num_types





def train_epoch(model, training_data, optimizer, opt):
    """ Epoch operation in training phase. """

    model.train()

    num_iter = 0 # number of batches per epoch


    for batch in tqdm(training_data, mininterval=2,
                      desc='  - (Training)   ', leave=False):

        num_iter += 1
        """ prepare data """
        _,_, event_type = map(lambda x: x.to(opt.device), batch)
        
        event_type_0 = torch.hstack([torch.zeros(event_type.shape[0],1).int().to('cuda'),event_type])

        """ forward """
        optimizer.zero_grad()

        output, _ = model(event_type_0)
        
        
        """ backward """

        loss = -log_likelihood(model, output[:,:-1,:], event_type )

        loss.backward()

        """ update parameters """
        optimizer.step()
    

    return -loss


def eval_epoch(model, validation_data, opt, event_interest):
    """ Epoch operation in evaluation phase. """

    model.eval()
    
    total_event_ll =0 # total loglikelihood
    num_iter = 0
    with torch.no_grad():
        for batch in tqdm(validation_data, mininterval=2,
                          desc='  - (Validation) ', leave=False):

            num_iter +=1
#             print(num_iter)
            """ prepare data """
            _,_, event_type = map(lambda x: x.to(opt.device), batch)
            
            event_type_0 = torch.hstack([torch.zeros(event_type.shape[0],1).int().to('cuda'),event_type])

            """ forward """
            
            output, _= model(event_type_0 )
            
            
            """ compute loss """

            event_ll = log_likelihood_event(model, output[:,:-1,:], event_type, event_interest)
            
            total_event_ll +=  event_ll
            

    return  total_event_ll 


def train(model, training_data, validation_data, test_data, optimizer, scheduler, opt, event_interest):
    """ Start training. """
    
    best_ll = -np.inf
    best_model = deepcopy(model.state_dict())

    train_ll_list = [] # train log likelihood
    valid_ll_list = [] # valid log likelihood
    impatience = 0 
    for epoch_i in range(opt.epoch):
        epoch = epoch_i + 1
        print('[ Epoch', epoch, ']')

        start = time.time()
        train_ll = train_epoch(model, training_data, optimizer, opt )
        
        train_ll_list +=[train_ll]
        
        print('  - (Training)     loglikelihood: {ll: 8.4f} ,'
              'elapse: {elapse:3.3f} min'
              .format( ll=train_ll, elapse=(time.time() - start) / 60))
        
    
        start = time.time()
        
        valid_ll = eval_epoch(model, validation_data, opt, event_interest )
        valid_ll_list += [valid_ll]
        print('  - (validation)  loglikelihood: {ll: 8.4f}'
              'elapse: {elapse:3.3f} min'
              .format( ll= valid_ll, elapse=(time.time() - start) / 60))

        start = time.time()
        
        test_ll = eval_epoch(model, test_data, opt, event_interest )
        print('  - (test)  loglikelihood: {ll: 8.4f}'
              'elapse: {elapse:3.3f} min'
              .format( ll= test_ll, elapse=(time.time() - start) / 60))
        
        print('  - [Info] Maximum validation loglikelihood:{ll: 8.4f} '
              .format(ll = max(valid_ll_list) ))
        

        if (valid_ll- best_ll ) < 1e-4:
            impatient += 1
            if best_ll < valid_ll:
                best_ll = valid_ll
                best_model = deepcopy(model.state_dict())
        else:
            best_ll = valid_ll
            best_model = deepcopy(model.state_dict())
            impatient = 0
        
            
        if impatient >= 5:
            print(f'Breaking due to early stopping at epoch {epoch}')
            break
    

        
        scheduler.step()
    

    return best_model
        
def get_non_pad_mask(seq):
    """ Get the non-padding positions. """

    assert seq.dim() == 2
    return seq.ne(Constants.PAD).type(torch.float).unsqueeze(-1)

def log_likelihood(model, data, types):
    """ Log-likelihood of sequence. """

    non_pad_mask = get_non_pad_mask(types).squeeze(2)

    all_hid = model.linear(data)
    
    all_scores = F.log_softmax(all_hid,dim=-1)
    types_3d =  F.one_hot(types, num_classes= model.num_types+1)
  
    ll = (all_scores*types_3d[:,:,1:]) #[:,1:,:]
    
    ll2 = torch.sum(ll,dim=-1)*non_pad_mask
    ll3 = torch.mean(torch.sum(ll2,dim=-1))

    return ll3



def log_likelihood_event(model, data, types, event_interest):
    """ Log-likelihood of observing event of interest in the sequence. """


    non_pad_mask = get_non_pad_mask(types).squeeze(2)
   
    all_hid = model.linear(data)

    all_scores = F.softmax(all_hid,dim=-1)
    all_scores_event = torch.log(all_scores[:,:,event_interest-1] +1e-12)
    all_scores_nonevent = torch.log(1 - all_scores[:,:,event_interest-1] +1e-12 )

    event_log_ll = (types == event_interest) * all_scores_event
    nonevent_log_ll = (types != event_interest) * all_scores_nonevent
    ll = (event_log_ll + nonevent_log_ll)*non_pad_mask#[:,1:]
    ll2 = torch.sum(ll)

    return ll2


def main():
    """ Main function. """

    parser = argparse.ArgumentParser()
#     parser.add_argument('-device', required=True)
    parser.add_argument('-data', required=True)
    
    parser.add_argument('-epoch', type=int, default=30)
    parser.add_argument('-batch_size', type=int, default=16)

    parser.add_argument('-d_model', type=int, default=64)
    parser.add_argument('-d_inner', type=int, default=128)
    parser.add_argument('-d_k', type=int, default=16)
    parser.add_argument('-d_v', type=int, default=16)

    parser.add_argument('-n_head', type=int, default=4)
    parser.add_argument('-n_layers', type=int, default=4)

    parser.add_argument('-dropout', type=float, default=0.01)
    parser.add_argument('-lr', type=float, default=1e-4)
    parser.add_argument('-log', type=str, default='log.txt')

    
    opt = parser.parse_args()

    # default device is CUDA
#     opt.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # default device is CUDA temporary
    opt.device = torch.device("cuda")


    print('[Info] parameters: {}'.format(opt))

    np.random.seed(0)
    torch.manual_seed(0)

    """ prepare dataloader """
    trainloader, devloader, testloader, num_types = prepare_dataloader(opt)


    """ prepare model """
    model = Transformer(
        num_types=num_types,
        d_model=opt.d_model,
        d_inner=opt.d_inner,
        n_layers=opt.n_layers,
        n_head=opt.n_head,
        d_k=opt.d_k,
        d_v=opt.d_v,
        dropout=opt.dropout,
    )
    model.to(opt.device)

    """ optimizer and scheduler """
    optimizer = optim.Adam(filter(lambda x: x.requires_grad, model.parameters()),
                            opt.lr, betas=(0.9, 0.999), eps=1e-08)

    scheduler = optim.lr_scheduler.StepLR(optimizer, 10, gamma=0.9)


    """ number of parameters """
    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print('[Info] Number of parameters: {}'.format(num_params))


    """ train each model @ each threshold """
    for event_interest in np.arange(1,num_types+1):

        best_model = train(model, trainloader, devloader, testloader, optimizer, scheduler, opt,  event_interest)

        model.load_state_dict(best_model)

        model.eval()

        valid_ll = eval_epoch(model, devloader, opt, event_interest)

        test_ll = eval_epoch(model, testloader, opt, event_interest)


        print("test log likelihood is {}".format(test_ll))

        # logging
        with open(opt.log, 'a') as f:
            f.write(' {event_interest}, {valid: 8.5f}, {test: 8.5f} \n'
                    .format( event_interest = event_interest, valid=valid_ll, test=test_ll))



import time
start = time.time()
np.random.seed(0)
torch.manual_seed(0)

if __name__ == '__main__':
    main()
end= time.time()
print("total training time is {}".format(end-start))

