#!/usr/bin/env python
# coding: utf-8
from simpletransformers.config.model_args import ModelArgs
from dataclasses import asdict, dataclass, field, fields
@dataclass
class MyMultiLabelClassificationArgs(ModelArgs):
    """
    Model args for a MultiLabelClassificationModel
    """

    model_class: str = "MyMultiLabelClassificationModel"
    sliding_window: bool = False
    stride: float = 0.8
    threshold: float = 0.5
    tie_value: int = 1
    labels_list: list = field(default_factory=list)
    labels_map: dict = field(default_factory=dict)
    lazy_loading: bool = False
    special_tokens_list: list = field(default_factory=list)
    #num_sublabels_per_biglabel: list = field(default_factory=list)

import torch
from torch import nn
from torch.nn import BCEWithLogitsLoss, CrossEntropyLoss, MSELoss
from transformers import (
    BertModel,
    BertPreTrainedModel
)
from transformers.modeling_utils import PreTrainedModel, SequenceSummary
from torch.nn.init import constant_, xavier_normal_, xavier_uniform_

class MyAttentionOutput(torch.nn.Module):
    def __init__(self, hidden_size, num_sublabels_per_biglabel, num_labels, device=None, dtype=None) -> None:
        factory_kwargs = {'device': device, 'dtype': dtype}
        super(MyAttentionOutput, self).__init__()
        self.hidden_size = hidden_size
        self.num_labels = num_labels
        self.num_sublabels_per_biglabel = num_sublabels_per_biglabel
        self.seqvec_to_query_linear = torch.nn.Linear(hidden_size, hidden_size, **factory_kwargs)
        self.output_classifier = torch.nn.Linear(hidden_size*2, max(num_sublabels_per_biglabel), **factory_kwargs)

    

    def forward(self, outputs, pooled_output):
        pooled_output = pooled_output.view(outputs[0].shape[0], -1, self.hidden_size)
        seqvec_for_every_label = pooled_output.repeat([1, len(self.num_sublabels_per_biglabel),1])
        seqvec_for_every_label_transformed = self.seqvec_to_query_linear(seqvec_for_every_label)
        seqvec_for_every_label_transformed += seqvec_for_every_label
        att_output = torch.nn.functional._scaled_dot_product_attention(seqvec_for_every_label_transformed, outputs[0], outputs[0])
        concated = torch.concat([att_output[0], seqvec_for_every_label], dim=-1)
        outputs_for_labelxclasses = self.output_classifier(concated)
        logits = torch.zeros((outputs_for_labelxclasses.shape[0], self.num_labels), device=outputs_for_labelxclasses.device)
        shift = 0
        assert len(outputs_for_labelxclasses.shape)==3 and outputs_for_labelxclasses.shape[1]==len(self.num_sublabels_per_biglabel)
        for i, num_sublabels in enumerate(self.num_sublabels_per_biglabel):
            logits[:,shift:shift + num_sublabels] = outputs_for_labelxclasses[:,i,:num_sublabels]
            shift += num_sublabels
        assert shift == self.num_labels
        return logits

class MyBertForMultiLabelSequenceClassification(BertPreTrainedModel):
    """
    Bert model adapted for multi-label sequence classification
    """

    def __init__(self, config, pos_weight=None, num_sublabels_per_biglabel=[], add_attention_for_labels=False, device=None, dtype=None):
        super(MyBertForMultiLabelSequenceClassification, self).__init__(config)
        factory_kwargs = {'device': device, 'dtype': dtype}
        self.num_labels = config.num_labels
        #print(config)
        self.num_sublabels_per_biglabel = num_sublabels_per_biglabel
        self.add_attention_for_labels = add_attention_for_labels


        if self.add_attention_for_labels:
            #self.bert = BertModel(config, add_pooling_layer = False)
            self.bert = BertModel(config, add_pooling_layer = True)
            self.dropout = nn.Dropout(config.hidden_dropout_prob)
            self.myattentionoutput = MyAttentionOutput(config.hidden_size, num_sublabels_per_biglabel, config.num_labels)
            #self.label_query_weights = torch.nn.Parameter(torch.empty((len(num_sublabels_per_biglabel), config.hidden_size), **factory_kwargs))  # batch?
            #self.output_classifier_weights = torch.nn.Parameter(torch.empty((config.hidden_size * 2, max(num_sublabels_per_biglabel)), **factory_kwargs))  # batch?
            #self.label_query_weights = torch.nn.Parameter(data=torch.Tensor(len(num_sublabels_per_biglabel), config.hidden_size), requires_grad=True)  # batch?
            #self.output_classifier_weights = torch.nn.Parameter(data=torch.Tensor(config.hidden_size * 2, max(num_sublabels_per_biglabel)), requires_grad=True)  # batch?
            #self.classifier = nn.Linear(config.hidden_size, self.config.num_labels)
        else:
            self.bert = BertModel(config)
            self.dropout = nn.Dropout(config.hidden_dropout_prob)
            self.classifier = nn.Linear(config.hidden_size, self.config.num_labels)
        self.pos_weight = pos_weight


        self.init_weights()

    def _reset_parameters(self):
        if self.add_attention_for_labels:
            xavier_uniform_(self.label_query_weights)
            xavier_uniform_(self.output_classifier_weights)

    def forward(
        self,
        input_ids,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        head_mask=None,
        labels=None,
    ):
        outputs = self.bert(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
        )
        pooled_output = outputs[1]
        pooled_output = self.dropout(pooled_output)
        if self.add_attention_for_labels:
            """
            att_output = torch.nn.functional._scaled_dot_product_attention(self.label_query_weights, outputs[0], outputs[0])
            seqvec_for_every_label = pooled_output.repeat([len(self.num_sublabels_per_biglabel),1])
            concated = torch.concat([att_output[0], seqvec_for_every_label], dim=-1)
            outputs_for_labelxclasses = torch.bmm(concated, self.output_classifier_weights)
            logits = torch.zeros(self.num_labels)
            shift = 0
            assert len(outputs_for_labelxclasses.shape)==2, outputs_for_labelxclasses.shape[0]==len(self.num_sublabels_per_biglabel)
            for i, num_sublabels in enumerate(self.num_sublabels_per_biglabel):
                logits[shift:shift + num_sublabels] = outputs_for_labelxclasses[i,:num_sublabels]
                shift += num_sublabels
            assert shift == self.num_labels
            """
            logits = self.myattentionoutput(outputs, pooled_output)
        else:            
            logits = self.classifier(pooled_output)
        outputs = (logits,) + outputs[
            2:
        ]  # add hidden states and attention if they are here
        if labels is not None:
            losses = []
            shift = 0
            logits = logits.view(-1, self.num_labels)
            labels = labels.float()
            labels = labels.view(-1, self.num_labels)
            pos_weight = None
            for num_sublabels in self.num_sublabels_per_biglabel:
                if self.pos_weight is not None:
                    pos_weight = self.pos_weight[shift:shift + num_sublabels]
                loss_fct = CrossEntropyLoss(weight=pos_weight)
                biglabel_logits = logits[:, shift:shift + num_sublabels]
                biglabel_labels = labels[:, shift:shift + num_sublabels]
                loss = loss_fct(biglabel_logits, biglabel_labels)
                losses.append(loss)
                shift += num_sublabels
            assert shift == self.num_labels
            loss = sum(losses) / len(losses)
            outputs = (loss,) + outputs

        return outputs  # (loss), logits, (hidden_states), (attentions)


import logging
import os
import random
import warnings
from multiprocessing import cpu_count

import numpy as np
import torch
from transformers import (
    WEIGHTS_NAME,
    BertConfig,
    BertTokenizer
)
from simpletransformers.classification import ClassificationModel
from simpletransformers.config.global_args import global_args
from simpletransformers.config.model_args import MultiLabelClassificationArgs
from simpletransformers.config.utils import sweep_config_to_sweep_values
from simpletransformers.custom_models.models import (
    BertForMultiLabelSequenceClassification
)
from simpletransformers.classification.multi_label_classification_model import MultiLabelClassificationModel

try:
    import wandb

    wandb_available = True
except ImportError:
    wandb_available = False

logger = logging.getLogger(__name__)


class MyMultiLabelClassificationModel(MultiLabelClassificationModel):
    def __init__(
        self,
        model_type,
        model_name,
        num_labels=None,
        pos_weight=None,
        args=None,
        use_cuda=True,
        cuda_device=-1,
        **kwargs,
    ):

        """
        Initializes a MultiLabelClassification model.
        Args:
            model_type: The type of model (bert, roberta)
            model_name: Default Transformer model name or path to a directory containing Transformer model file (pytorch_nodel.bin).
            num_labels (optional): The number of labels or classes in the dataset.
            pos_weight (optional): A list of length num_labels containing the weights to assign to each label for loss calculation.
            args (optional): Default args will be used if this parameter is not provided. If provided, it should be a dict containing the args that should be changed in the default args.
            use_cuda (optional): Use GPU if available. Setting to False will force model to use CPU only.
            cuda_device (optional): Specific GPU that should be used. Will use the first available GPU by default.
            **kwargs (optional): For providing proxies, force_download, resume_download, cache_dir and other options specific to the 'from_pretrained' implementation where this will be supplied.
        """  # noqa: ignore flake8"

        MODEL_CLASSES = {
            "bert": (
                BertConfig,
                MyBertForMultiLabelSequenceClassification,
                BertTokenizer,
            )
        }

        self.args = self._load_model_args(model_name)

        if isinstance(args, dict):
            self.args.update_from_dict(args)
        elif isinstance(args, MultiLabelClassificationArgs):
            self.args = args
        elif isinstance(args, MyMultiLabelClassificationArgs):
            self.args = args

        if self.args.thread_count:
            torch.set_num_threads(self.args.thread_count)

        if "sweep_config" in kwargs:
            self.is_sweeping = True
            sweep_config = kwargs.pop("sweep_config")
            sweep_values = sweep_config_to_sweep_values(sweep_config)
            self.args.update_from_dict(sweep_values)
        else:
            self.is_sweeping = False

        if self.args.manual_seed:
            random.seed(self.args.manual_seed)
            np.random.seed(self.args.manual_seed)
            torch.manual_seed(self.args.manual_seed)
            if self.args.n_gpu > 0:
                torch.cuda.manual_seed_all(self.args.manual_seed)

        if not use_cuda:
            self.args.fp16 = False

        config_class, model_class, tokenizer_class = MODEL_CLASSES[model_type]
        if num_labels:
            self.config = config_class.from_pretrained(
                model_name, num_labels=num_labels, **self.args.config
            )
            self.num_labels = num_labels
        else:
            self.config = config_class.from_pretrained(model_name, **self.args.config)
            self.num_labels = self.config.num_labels
        self.pos_weight = pos_weight
        self.loss_fct = None

        if use_cuda:
            if torch.cuda.is_available():
                if cuda_device == -1:
                    self.device = torch.device("cuda")
                else:
                    self.device = torch.device(f"cuda:{cuda_device}")
            else:
                raise ValueError(
                    "'use_cuda' set to True when cuda is unavailable."
                    " Make sure CUDA is available or set use_cuda=False."
                )
        else:
            self.device = "cpu"

        if not self.args.quantized_model:
            if self.pos_weight:
                self.model = model_class.from_pretrained(
                    model_name,
                    config=self.config,
                    pos_weight=torch.Tensor(self.pos_weight).to(self.device),
                    **kwargs,
                )
            else:
                self.model = model_class.from_pretrained(
                    model_name, config=self.config, **kwargs
                )
        else:
            quantized_weights = torch.load(
                os.path.join(model_name, "pytorch_model.bin")
            )
            if self.pos_weight:
                self.model = model_class.from_pretrained(
                    None,
                    config=self.config,
                    state_dict=quantized_weights,
                    weight=torch.Tensor(self.pos_weight).to(self.device),
                )
            else:
                self.model = model_class.from_pretrained(
                    None, config=self.config, state_dict=quantized_weights
                )

        if self.args.dynamic_quantize:
            self.model = torch.quantization.quantize_dynamic(
                self.model, {torch.nn.Linear}, dtype=torch.qint8
            )
        if self.args.quantized_model:
            self.model.load_state_dict(quantized_weights)
        if self.args.dynamic_quantize:
            self.args.quantized_model = True

        self.results = {}

        self.tokenizer = tokenizer_class.from_pretrained(
            model_name, do_lower_case=self.args.do_lower_case, **kwargs
        )

        if self.args.special_tokens_list:
            self.tokenizer.add_tokens(
                self.args.special_tokens_list, special_tokens=True
            )
            self.model.resize_token_embeddings(len(self.tokenizer))

        self.args.model_name = model_name
        self.args.model_type = model_type

        if self.args.wandb_project and not wandb_available:
            warnings.warn(
                "wandb_project specified but wandb is not available. Wandb disabled."
            )
            self.args.wandb_project = None

        self.weight = None  # Not implemented for multilabel