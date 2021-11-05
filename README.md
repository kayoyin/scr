# Signed Coreference Resolution

This repository gathers the code, data and annotation interface for [Signed Coreference Resolution](https://aclanthology.org/2021.emnlp-main.405/)

To run the multigraph model:
```bash
    python run-multigraph.py -in dgs-coref/data.json -out multigraph.out 
```

To evaluate the outputs:
```bash
    python format_conll.py --data dgs-coref/data.json --key >  multigraph.key
    python format_conll.py --data  multigraph.out >  multigraph.answer
    perl scorer.pl all multigraph.key  multigraph.answer >  multigraph.score
```

Please cite the paper below if you found the resources in this repository useful:

```
@inproceedings{yin-etal-2021-signed,
    title = "Signed Coreference Resolution",
    author = "Yin, Kayo  and
      DeHaan, Kenneth  and
      Alikhani, Malihe",
    booktitle = "Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing",
    month = nov,
    year = "2021",
    address = "Online and Punta Cana, Dominican Republic",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2021.emnlp-main.405",
    pages = "4950--4961",
}
```