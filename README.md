W266 Final Project

Starter code, dataset, etc via UniCausal

To run:

!python run_tokbase.py \
  --model_name_or_path SpanBERT/spanbert-base-cased \
  --dataset_name because altlex  \
  --do_train \
  --do_eval \
  --do_predict \
  --do_train_val \
  --task_name 'ce' \
  --num_train_epochs 10 \
  --output_dir 'your_output_dir_here'
