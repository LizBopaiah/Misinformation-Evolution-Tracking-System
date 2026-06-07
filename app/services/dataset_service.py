import os
import json
import pandas as pd

class DatasetService:
    """Service class for managing, validating, loading, and previewing project datasets"""
    
    def __init__(self, root_dir=None):
        if root_dir is None:
            self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        else:
            self.root_dir = root_dir
            
        self.paths = {
            "fake_news": {
                "fake": os.path.join(self.root_dir, "Fake News Detection", "Fake.csv"),
                "true": os.path.join(self.root_dir, "Fake News Detection", "True.csv")
            },
            "liar": {
                "train": os.path.join(self.root_dir, "LIAR Dataset", "train.tsv"),
                "test": os.path.join(self.root_dir, "LIAR Dataset", "test.tsv"),
                "valid": os.path.join(self.root_dir, "LIAR Dataset", "valid.tsv")
            },
            "emotion": {
                "train": os.path.join(self.root_dir, "Emotion Dataset", "train.txt"),
                "test": os.path.join(self.root_dir, "Emotion Dataset", "test.txt"),
                "val": os.path.join(self.root_dir, "Emotion Dataset", "val.txt")
            }
        }
        
        self.cache_path = os.path.join(self.root_dir, "instance", "dataset_stats.json")
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)

    def validate_datasets(self, force=False):
        """
        Validates the presence, row counts, missing values, and label distribution of all datasets.
        Caches statistics to avoid reprocessing large CSV files on every startup.
        """
        if not force and os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    cached_stats = json.load(f)
                # Quick verification that folders/files listed as loaded still exist
                all_exist = True
                for ds in ["fake_news", "liar", "emotion"]:
                    if ds in cached_stats and cached_stats[ds].get("status") == "Loaded":
                        for fpath in self.paths[ds].values():
                            if not os.path.exists(fpath):
                                all_exist = False
                if all_exist:
                    return cached_stats
            except Exception:
                pass # Cache invalid, re-run validation

        report = {
            "fake_news": {"status": "Missing", "records": 0, "missing_values": 0, "labels": {}},
            "liar": {"status": "Missing", "records": 0, "missing_values": 0, "labels": {}},
            "emotion": {"status": "Missing", "records": 0, "missing_values": 0, "labels": {}},
            "health": "Healthy"
        }

        # 1. Validate Fake News
        fn_paths = self.paths["fake_news"]
        if os.path.exists(fn_paths["fake"]) and os.path.exists(fn_paths["true"]):
            try:
                df_fake = pd.read_csv(fn_paths["fake"])
                df_true = pd.read_csv(fn_paths["true"])
                
                records = len(df_fake) + len(df_true)
                missing = int(df_fake.isna().sum().sum() + df_true.isna().sum().sum())
                
                report["fake_news"] = {
                    "status": "Loaded",
                    "records": records,
                    "missing_values": missing,
                    "labels": {
                        "Real": len(df_true),
                        "Fake": len(df_fake)
                    }
                }
            except Exception as e:
                report["fake_news"] = {"status": f"Error: {str(e)}", "records": 0, "missing_values": 0, "labels": {}}
                report["health"] = "Unhealthy"

        # 2. Validate LIAR
        liar_paths = self.paths["liar"]
        if all(os.path.exists(liar_paths[k]) for k in ["train", "test", "valid"]):
            try:
                dfs = []
                for k in ["train", "test", "valid"]:
                    dfs.append(pd.read_csv(liar_paths[k], sep='\t', header=None))
                df_liar = pd.concat(dfs, ignore_index=True)
                
                # Column 1 contains labels, Column 2 contains statements
                labels_series = df_liar[1]
                missing = int(df_liar[[1, 2]].isna().sum().sum())
                
                # Map labels
                mapped_labels = labels_series.map(self._map_liar_label)
                label_counts = mapped_labels.value_counts().to_dict()
                
                report["liar"] = {
                    "status": "Loaded",
                    "records": len(df_liar),
                    "missing_values": missing,
                    "labels": {str(k): int(v) for k, v in label_counts.items()}
                }
            except Exception as e:
                report["liar"] = {"status": f"Error: {str(e)}", "records": 0, "missing_values": 0, "labels": {}}
                report["health"] = "Unhealthy"

        # 3. Validate Emotion
        em_paths = self.paths["emotion"]
        if all(os.path.exists(em_paths[k]) for k in ["train", "test", "val"]):
            try:
                dfs = []
                for k in ["train", "test", "val"]:
                    dfs.append(pd.read_csv(em_paths[k], sep=';', header=None, names=['text', 'label']))
                df_emotion = pd.concat(dfs, ignore_index=True)
                
                missing = int(df_emotion.isna().sum().sum())
                label_counts = df_emotion['label'].map(lambda x: str(x).capitalize()).value_counts().to_dict()
                
                report["emotion"] = {
                    "status": "Loaded",
                    "records": len(df_emotion),
                    "missing_values": missing,
                    "labels": {str(k): int(v) for k, v in label_counts.items()}
                }
            except Exception as e:
                report["emotion"] = {"status": f"Error: {str(e)}", "records": 0, "missing_values": 0, "labels": {}}
                report["health"] = "Unhealthy"

        # Cache report
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=4)
        except Exception:
            pass

        return report

    def get_preview(self):
        """Returns a small sample (5 records) of each dataset for preview"""
        preview = {"fake_news": [], "liar": [], "emotion": []}

        # 1. Fake news preview
        try:
            fn_paths = self.paths["fake_news"]
            if os.path.exists(fn_paths["fake"]) and os.path.exists(fn_paths["true"]):
                df_fake = pd.read_csv(fn_paths["fake"]).head(3)
                df_true = pd.read_csv(fn_paths["true"]).head(2)
                for _, row in df_fake.iterrows():
                    preview["fake_news"].append({"text": str(row['text'])[:150] + "...", "label": "Fake"})
                for _, row in df_true.iterrows():
                    preview["fake_news"].append({"text": str(row['text'])[:150] + "...", "label": "Real"})
        except Exception:
            pass

        # 2. LIAR preview
        try:
            liar_paths = self.paths["liar"]
            if os.path.exists(liar_paths["train"]):
                df_liar = pd.read_csv(liar_paths["train"], sep='\t', header=None).head(5)
                for _, row in df_liar.iterrows():
                    preview["liar"].append({
                        "text": str(row[2])[:150] + "...",
                        "label": self._map_liar_label(row[1])
                    })
        except Exception:
            pass

        # 3. Emotion preview
        try:
            em_paths = self.paths["emotion"]
            if os.path.exists(em_paths["train"]):
                df_emotion = pd.read_csv(em_paths["train"], sep=';', header=None, names=['text', 'label']).head(5)
                for _, row in df_emotion.iterrows():
                    preview["emotion"].append({
                        "text": str(row['text'])[:150] + "...",
                        "label": str(row['label']).capitalize()
                    })
        except Exception:
            pass

        return preview

    def load_fake_news_df(self):
        """Loads and returns Fake News DataFrame with standard columns ['text', 'label']"""
        fn_paths = self.paths["fake_news"]
        df_fake = pd.read_csv(fn_paths["fake"])
        df_true = pd.read_csv(fn_paths["true"])
        
        df_fake['label'] = 1  # 1 = Fake
        df_true['label'] = 0  # 0 = Real
        
        df = pd.concat([df_fake, df_true], ignore_index=True)
        return df[['text', 'label']].rename(columns={'text': 'text'})

    def load_liar_df(self):
        """Loads and returns LIAR Dataset DataFrame with standard columns ['text', 'label']"""
        liar_paths = self.paths["liar"]
        dfs = []
        for k in ["train", "test", "valid"]:
            dfs.append(pd.read_csv(liar_paths[k], sep='\t', header=None))
        df_liar = pd.concat(dfs, ignore_index=True)
        
        df = pd.DataFrame({
            'text': df_liar[2],
            'label': df_liar[1].map(self._map_liar_label)
        })
        return df.dropna(subset=['text', 'label'])

    def load_emotion_df(self):
        """Loads and returns Emotion Dataset DataFrame with standard columns ['text', 'label']"""
        em_paths = self.paths["emotion"]
        dfs = []
        for k in ["train", "test", "val"]:
            dfs.append(pd.read_csv(em_paths[k], sep=';', header=None, names=['text', 'label']))
        df_emotion = pd.concat(dfs, ignore_index=True)
        
        df_emotion['label'] = df_emotion['label'].map(lambda x: str(x).capitalize())
        return df_emotion[['text', 'label']]

    def _map_liar_label(self, label):
        """Map LIAR tsv labels to True, Partially True, or False"""
        label = str(label).lower().strip()
        if label == "true":
            return "True"
        elif label in ["mostly-true", "half-true", "barely-true"]:
            return "Partially True"
        else:
            return "False"
